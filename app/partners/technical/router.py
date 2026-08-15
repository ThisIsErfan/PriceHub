"""Technical partner endpoints — mounted at /v1/technical by app.main.

All routes are GET and require an ACTIVE key scoped to the `technical` partner.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_partner
from app.db.session import get_session
from app.partners.technical import service
from app.shared.schemas import ok

SLUG = "technical"
router = APIRouter(tags=["technical"])

_auth_prices = Depends(require_partner(SLUG, scope="prices:read"))

# Shared help text for the `asset` input — the same slug as today; the standard
# symbol (XAU/XAG/XCU) is returned in the response, not required as input.
_ASSET_DESC = "Asset slug, e.g. gold-18k (طلا), silver-999 (نقره), copper (مس)"
# Currency input is the slug too — the lowercase code (irt, irr, usd), so both
# inputs are spelled the same way. An uppercase code still matches.
_CURRENCY_DESC = "Currency slug (lowercase code), e.g. irt, irr, usd"


@router.get(
    "/prices/platforms/latest",
    summary="Latest quote per platform/asset/currency — bid/ask + standard symbol",
)
async def platforms_latest(
    _ctx=_auth_prices,
    source: Optional[str] = Query(None, description="Filter by platform (source) slug"),
    asset: Optional[str] = Query(None, description=f"Filter by {_ASSET_DESC}"),
    currency: Optional[str] = Query(None, description=f"Filter by {_CURRENCY_DESC}"),
    type: Optional[str] = Query(None, description="Filter by asset type"),
    assets: Optional[str] = Query(None, description="Filter by a comma-separated list of asset slugs"),
    session: AsyncSession = Depends(get_session),
):
    return ok(
        await service.all_latest_prices(
            session, source=source, asset=asset, currency=currency, type=type, assets=assets
        )
    )


@router.get("/prices/suppliers/latest", summary="Latest supplier buy/sell quotes")
async def suppliers_latest(
    _ctx=_auth_prices,
    source: Optional[str] = Query(None, description="Filter by supplier slug"),
    asset: Optional[str] = Query(None, description=f"Filter by {_ASSET_DESC}"),
    session: AsyncSession = Depends(get_session),
):
    return ok(await service.supplier_latest(session, source=source, asset=asset))


@router.get(
    "/prices/stats",
    summary="Cross-source statistical summary (mean/median/2σ/3σ trimmed/min/max) per asset/currency",
)
async def prices_stats(
    _ctx=_auth_prices,
    asset: Optional[str] = Query(None, description=f"Filter by {_ASSET_DESC}; omit for every asset"),
    currency: Optional[str] = Query(None, description=f"Filter by {_CURRENCY_DESC}; omit for every currency"),
    max_age_seconds: int = Query(
        180, ge=30, le=3600,
        description="Exclude sources not updated within this many seconds (default 180 = 3min)",
    ),
    role: Optional[str] = Query(None, description="Restrict to a source role: platform|reference"),
    session: AsyncSession = Depends(get_session),
):
    return ok(
        await service.price_stats(
            session, asset=asset, currency=currency,
            max_age_seconds=max_age_seconds, role=role,
        )
    )
