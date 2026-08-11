"""SEO partner endpoints — mounted at /v1/seo by app.main.

All routes are GET and require an ACTIVE key scoped to the `seo` partner.

  * GET /price-page — the site's price page: every row of
    seo_schm.talasea_gold_prices (gold + coin tables, all columns), with the
    18k-gram row's numeric fields rebuilt from the gerami source.
  * GET /prices/latest — latest platform quote for the featured SEO assets, in
    the standard item shape (see app.shared.refs).
  * GET /news — recent metals news headlines.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_partner
from app.db.session import get_session
from app.partners.seo import service
from app.shared.schemas import ok

SLUG = "seo"
router = APIRouter(tags=["seo"])

_auth_prices = Depends(require_partner(SLUG, scope="prices:read"))
_auth_news = Depends(require_partner(SLUG, scope="news:read"))


@router.get(
    "/price-page",
    summary="SEO price page — gold & coin tables (latest snapshot; 18k from gerami)",
)
async def price_page(
    _ctx=_auth_prices,
    session: AsyncSession = Depends(get_session),
):
    return ok(await service.price_page(session))


@router.get(
    "/prices/latest",
    summary="Latest quote for the featured SEO assets (platform sources only)",
)
async def prices_latest(
    _ctx=_auth_prices,
    asset: Optional[str] = Query(
        None,
        description=(
            "Limit to one asset slug, e.g. gold-18k (طلا), silver-999 (نقره). "
            "Omit for the whole featured set."
        ),
    ),
    session: AsyncSession = Depends(get_session),
):
    return ok(await service.featured_prices(session, asset=asset))


@router.get("/news", summary="Recent metals news headlines")
async def news(
    _ctx=_auth_news,
    symbol: Optional[str] = Query(
        None, description="Filter by metal symbol slug: gold | silver | copper"
    ),
    limit: int = Query(20, ge=1, le=50, description="How many articles (max 50)"),
    session: AsyncSession = Depends(get_session),
):
    return ok(await service.recent_news(session, symbol=symbol, limit=limit))
