"""Durable per-partner usage counting — the source of truth for "how many calls".

Every successful authenticated request is rolled up into
``partner_schm.partner_usage_daily`` via a single UPSERT keyed by
(api_key_id, day, endpoint). One row per key/day/endpoint, its ``request_count``
incremented — so the table stays tiny (bounded by keys × days × endpoints) no
matter how many requests arrive, and answers reporting questions with plain SQL:

    -- calls per partner in the last 30 days
    SELECT p.slug, SUM(u.request_count)
    FROM   partner_schm.partner_usage_daily u
    JOIN   partner_schm.partner_api_keys k ON k.id = u.api_key_id
    JOIN   partner_schm.partners p         ON p.id = k.partner_id
    WHERE  u.day >= CURRENT_DATE - INTERVAL '30 days'
    GROUP  BY p.slug;

We also refresh the key's ``last_used_at`` here (cheap, same transaction).

This runs after the response is produced and must never break a request: any DB
error is swallowed (logged) so usage accounting can't turn a good response into a
failure. Redis holds the real-time rate-limit counters; this holds the durable
history — the two are deliberately separate stores.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("pricehub.usage")

_UPSERT_USAGE_SQL = text(
    """
    INSERT INTO partner_schm.partner_usage_daily (api_key_id, day, endpoint, request_count)
    VALUES (:api_key_id, CURRENT_DATE, :endpoint, 1)
    ON CONFLICT (api_key_id, day, endpoint)
    DO UPDATE SET request_count = partner_usage_daily.request_count + 1
    """
)

_TOUCH_KEY_SQL = text(
    "UPDATE partner_schm.partner_api_keys SET last_used_at = NOW() WHERE id = :api_key_id"
)


async def record_request(session: AsyncSession, api_key_id: int, endpoint: str) -> None:
    """Increment the durable usage counter for (key, today, endpoint).

    ``endpoint`` should be the stable route template (e.g. ``/v1/seo/prices``),
    not the concrete path, so counts group cleanly. Never raises.
    """
    try:
        await session.execute(_UPSERT_USAGE_SQL, {"api_key_id": api_key_id, "endpoint": endpoint})
        await session.execute(_TOUCH_KEY_SQL, {"api_key_id": api_key_id})
        await session.commit()
    except Exception:  # noqa: BLE001 — usage accounting must never fail a request
        await session.rollback()
        logger.warning("failed to record usage for key %s on %s", api_key_id, endpoint, exc_info=True)
