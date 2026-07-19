"""The partner authentication + rate-limit dependency.

`require_partner(module_slug, scope=...)` is what every partner route depends on.
For each request it, in order:

  1. reads the `X-API-Key` header (keys never travel in the query string);
  2. resolves it to an ACTIVE key belonging to an ACTIVE partner (one indexed
     lookup by SHA-256 hash — see app.core.security);
  3. enforces tenant isolation: the key's partner slug MUST equal the module it
     is calling, so a `seo` key can never reach `/v1/technical/*` (→ 403);
  4. (optional) checks the route's required scope against the key's scopes;
  5. enforces the per-second + per-minute rate limits in Redis (→ 429);
  6. stashes a PartnerContext on `request.state` so the usage middleware can
     record the call durably after the response is sent.

Auth failures raise HTTPException; the app's handlers wrap them in the standard
envelope (see app.main).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_api_key
from app.db.session import get_session
from app.usage.ratelimit import check_rate_limit

_MISSING_KEY = "API key required. Send it in the 'X-API-Key' header."
_INVALID_KEY = "Invalid or inactive API key."
_FORBIDDEN_PARTNER = "This API key is not authorised for this partner's endpoints."
_FORBIDDEN_SCOPE = "This API key lacks the scope required for this endpoint."
_RATE_LIMITED = "Rate limit exceeded. Slow down and retry."


@dataclass(frozen=True)
class PartnerContext:
    api_key_id: int
    partner_id: int
    partner_slug: str
    scopes: list[str]
    rate_limit_per_sec: int
    rate_limit_per_min: int


# Resolve an active key + its active partner in one lookup by key hash.
_LOOKUP_KEY_SQL = text(
    """
    SELECT k.id                  AS api_key_id,
           k.partner_id          AS partner_id,
           k.scopes              AS scopes,
           k.rate_limit_per_sec  AS rate_limit_per_sec,
           k.rate_limit_per_min  AS rate_limit_per_min,
           p.slug                AS partner_slug
    FROM   partner_schm.partner_api_keys k
    JOIN   partner_schm.partners p ON p.id = k.partner_id
    WHERE  k.key_hash = :key_hash
      AND  k.is_active = TRUE
      AND  k.revoked_at IS NULL
      AND  p.status = 'active'
    """
)


def require_partner(module_slug: str, scope: Optional[str] = None):
    """Build the auth+rate-limit dependency for a partner module.

    `module_slug` is the partner directory/namespace this router serves (e.g.
    "seo"). `scope` optionally names a permission the key must carry (e.g.
    "prices:read"); pass None to skip the scope check (relaxed while internal).
    """

    async def dependency(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        session: AsyncSession = Depends(get_session),
    ) -> PartnerContext:
        if not x_api_key:
            raise HTTPException(status_code=401, detail=_MISSING_KEY)

        row = (
            await session.execute(_LOOKUP_KEY_SQL, {"key_hash": hash_api_key(x_api_key)})
        ).mappings().first()
        if row is None:
            raise HTTPException(status_code=401, detail=_INVALID_KEY)

        # Tenant isolation: the key's partner must own the module being called.
        if row["partner_slug"] != module_slug:
            raise HTTPException(status_code=403, detail=_FORBIDDEN_PARTNER)

        scopes = list(row["scopes"] or [])
        if scope is not None and scope not in scopes:
            raise HTTPException(status_code=403, detail=_FORBIDDEN_SCOPE)

        per_sec = row["rate_limit_per_sec"] or settings.DEFAULT_RATE_LIMIT_PER_SEC
        per_min = row["rate_limit_per_min"] or settings.DEFAULT_RATE_LIMIT_PER_MIN

        decision = await check_rate_limit(row["api_key_id"], per_sec, per_min)
        if not decision.allowed:
            raise HTTPException(
                status_code=429,
                detail=_RATE_LIMITED,
                headers={"Retry-After": str(decision.retry_after)},
            )

        ctx = PartnerContext(
            api_key_id=row["api_key_id"],
            partner_id=row["partner_id"],
            partner_slug=row["partner_slug"],
            scopes=scopes,
            rate_limit_per_sec=per_sec,
            rate_limit_per_min=per_min,
        )
        # Handed to the usage middleware to record the call after the response.
        request.state.partner_ctx = ctx
        return ctx

    return dependency
