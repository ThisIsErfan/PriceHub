"""SEO partner endpoints — mounted at /v1/seo by app.main.

All routes are GET and require an ACTIVE key scoped to the `seo` partner.

  * GET /price-page — the site's price page: every row of
    seo_schm.talasea_gold_prices (gold + coin tables, all columns), with the
    18k-gram row's numeric fields rebuilt from the gerami source.

This is deliberately the SEO partner's ONLY surface. `service.featured_prices`
and `service.recent_news` are kept as reference implementations — already on the
shared response standard — but are NOT mounted; wiring one up is a route here
plus the matching scope on the key.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_partner
from app.db.session import get_session
from app.partners.seo import service
from app.shared.schemas import ok

SLUG = "seo"
router = APIRouter(tags=["seo"])

_auth_prices = Depends(require_partner(SLUG, scope="prices:read"))


@router.get(
    "/price-page",
    summary="SEO price page — gold & coin tables (latest snapshot; 18k from gerami)",
)
async def price_page(
    _ctx=_auth_prices,
    session: AsyncSession = Depends(get_session),
):
    return ok(await service.price_page(session))
