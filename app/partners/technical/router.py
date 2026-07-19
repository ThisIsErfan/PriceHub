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


@router.get(
    "/prices/latest",
    summary="Latest quote per source/asset/currency — same shape as copilot's platform-compare",
)
async def prices_latest(
    _ctx=_auth_prices,
    source: Optional[str] = Query(None, description="Filter by source (platform) slug"),
    asset: Optional[str] = Query(None, description="Filter by asset slug, e.g. gold-18k"),
    currency: Optional[str] = Query(None, description="Filter by currency code, e.g. IRT, IRR"),
    type: Optional[str] = Query(None, description="Filter by asset type"),
    assets: Optional[str] = Query(None, description="Filter by a comma-separated list of asset slugs"),
    session: AsyncSession = Depends(get_session),
):
    return ok(
        await service.all_latest_prices(
            session, source=source, asset=asset, currency=currency, type=type, assets=assets
        )
    )


@router.get(
    "/prices/compare",
    summary="Compare one asset's latest price across ALL sources",
)
async def prices_compare(
    _ctx=_auth_prices,
    asset: str = Query(..., description="Asset slug to compare, e.g. gold-18k (required)"),
    currency: Optional[str] = Query(None, description="Currency code, e.g. IRT, IRR"),
    session: AsyncSession = Depends(get_session),
):
    # Same shape as prices/latest, but scoped to one asset — "this asset across
    # every source". asset is required so the intent (comparison) is explicit.
    return ok(await service.all_latest_prices(session, asset=asset, currency=currency))


@router.get(
    "/prices/stats",
    summary="Cross-source statistical summary (mean/median/2σ/3σ trimmed/min/max) for one asset",
)
async def prices_stats(
    _ctx=_auth_prices,
    asset: str = Query(..., description="Asset slug, e.g. gold-18k (required)"),
    currency: str = Query(..., description="Currency code, e.g. IRT (required)"),
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


@router.get("/suppliers/latest", summary="Latest supplier buy/sell quotes")
async def suppliers_latest(
    _ctx=_auth_prices,
    source: Optional[str] = Query(None, description="Filter by supplier slug"),
    asset: Optional[str] = Query(None, description="Filter by asset slug"),
    session: AsyncSession = Depends(get_session),
):
    return ok(await service.supplier_latest(session, source=source, asset=asset))
