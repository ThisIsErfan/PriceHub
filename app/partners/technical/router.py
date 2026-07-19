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


@router.get("/suppliers/latest", summary="Latest supplier buy/sell quotes")
async def suppliers_latest(
    _ctx=_auth_prices,
    source: Optional[str] = Query(None, description="Filter by supplier slug"),
    asset: Optional[str] = Query(None, description="Filter by asset slug"),
    session: AsyncSession = Depends(get_session),
):
    return ok(await service.supplier_latest(session, source=source, asset=asset))
