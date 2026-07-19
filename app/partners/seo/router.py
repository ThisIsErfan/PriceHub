"""SEO partner endpoints — mounted at /v1/seo by app.main.

All routes are GET and require an ACTIVE key scoped to the `seo` partner. Scopes
are declared per route but relaxed while consumers are internal (the key simply
needs to belong to the `seo` partner).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_partner
from app.db.session import get_session
from app.partners.seo import service
from app.shared.data import prices as price_data
from app.shared.schemas import ok

SLUG = "seo"
router = APIRouter(tags=["seo"])

# One dependency instance per required scope, reused across routes.
_auth_prices = Depends(require_partner(SLUG, scope="prices:read"))
_auth_news = Depends(require_partner(SLUG, scope="news:read"))


@router.get("/prices/latest", summary="Latest price for the SEO featured assets")
async def prices_latest(
    _ctx=_auth_prices,
    asset: Optional[str] = Query(None, description="Filter to a single asset slug, e.g. gold-18k"),
    session: AsyncSession = Depends(get_session),
):
    return ok(await service.featured_prices(session, asset=asset))


@router.get("/assets", summary="Catalog of assets available to reference")
async def assets(
    _ctx=_auth_prices,
    type: Optional[str] = Query(None, description="Filter by type: gold|silver|coin|currency|crypto"),
    session: AsyncSession = Depends(get_session),
):
    return ok({"items": await price_data.list_assets(session, type=type)})


@router.get("/news", summary="Recent metals news headlines")
async def news(
    _ctx=_auth_news,
    symbol: Optional[str] = Query(None, description="Filter by metal: gold|silver|copper"),
    limit: int = Query(20, ge=1, le=50, description="Max articles (1-50)"),
    session: AsyncSession = Depends(get_session),
):
    return ok(await service.recent_news(session, symbol=symbol, limit=limit))
