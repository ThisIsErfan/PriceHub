"""Read queries over the SEO price-page schema (``seo_schm``).

Backs the ``/v1/seo/price-page`` feed. The table is a latest-only snapshot
(one row per instrument, upserted by the talasea gold/coin crawler), so there is
no history/DISTINCT logic — one plain SELECT returns the current page.

Runs as ``partner_api_usr`` (SELECT only; granted in
migrations/partner/R001__grants.sql). Returns JSON-ready dicts.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Page order: the site shows the gold table first, then coins; within a table,
# `id` preserves the on-page row order (rows were first inserted in that order,
# and the upsert keeps the id stable). raw_data / id / timestamps other than
# crawled_at are internal and not exposed.
_PAGE_SQL = text(
    """
    SELECT category,
           slug,
           name,
           unit,
           current_price,
           low_price,
           high_price,
           change_1d_percent,
           change_30d_percent,
           weekly_chart_path,
           crawled_at
    FROM   seo_schm.talasea_gold_prices
    ORDER  BY CASE category WHEN 'gold' THEN 0 ELSE 1 END, id
    """
)


async def talasea_gold_prices(session: AsyncSession) -> list[dict[str, Any]]:
    """Return every row of the SEO price-page table, in on-page order."""
    result = await session.execute(_PAGE_SQL)
    return [dict(r) for r in result.mappings().all()]


# The 18k gold row is served from the GERAMI source instead of the talasea
# scrape. Gerami is already crawled into price_schm.price_history, so — unlike
# its live API — we have the HISTORY needed to rebuild the very same fields the
# SEO table carries: current price, day low/high, and 1-day / 30-day change.
# All from one pass over the gerami 18k history.
_GERAMI_18K_SQL = text(
    """
    WITH g AS (
        SELECT ph.price AS price, ph.crawled_at AS crawled_at
        FROM   price_schm.price_history ph
        JOIN   price_schm.sources    s ON s.id = ph.source_id
        JOIN   price_schm.assets     a ON a.id = ph.asset_id
        JOIN   price_schm.currencies c ON c.id = ph.currency_id
        WHERE  s.slug = :source
          AND  a.slug = :asset
          AND  c.code = :currency
          AND  ph.price > 0            -- drop the "-1" no-quote sentinel
    )
    SELECT
        (SELECT price FROM g ORDER BY crawled_at DESC LIMIT 1)          AS current_price,
        (SELECT max(crawled_at) FROM g)                                 AS crawled_at,
        (SELECT min(price) FROM g WHERE crawled_at >= now() - interval '24 hours') AS low_price,
        (SELECT max(price) FROM g WHERE crawled_at >= now() - interval '24 hours') AS high_price,
        (SELECT price FROM g WHERE crawled_at <= now() - interval '24 hours'
             ORDER BY crawled_at DESC LIMIT 1)                          AS price_1d_ago,
        (SELECT price FROM g WHERE crawled_at <= now() - interval '30 days'
             ORDER BY crawled_at DESC LIMIT 1)                          AS price_30d_ago
    """
)


async def gerami_gold_18k(
    session: AsyncSession,
    *,
    source: str = "gerami",
    asset: str = "gold-18k",
    currency: str = "IRT",
) -> dict[str, Any] | None:
    """Rebuild the SEO price-page fields for 18k gold from the Gerami source.

    Returns a dict with `current_price`, `low_price`, `high_price`,
    `price_1d_ago`, `price_30d_ago`, `crawled_at` (the 1d/30d percentages are
    derived from the *_ago prices by the caller). Any field with no data is
    None. Returns None entirely when Gerami has no 18k history at all, so the
    caller can fall back to the stored talasea values.
    """
    row = (
        await session.execute(
            _GERAMI_18K_SQL, {"source": source, "asset": asset, "currency": currency}
        )
    ).mappings().first()
    if row is None or row["current_price"] is None:
        return None
    return dict(row)
