"""SEO partner endpoints — mounted at /v1/seo by app.main.

All routes are GET and require an ACTIVE key scoped to the `seo` partner.

  * GET /price-page — the site's price page: every row of
    seo_schm.talasea_gold_prices (gold + coin tables, all columns), with the
    18k-gram row's numeric fields rebuilt from the gerami source.

A reference implementation of featured-price / news routes is kept in
`service.py` for when those surfaces are wired up.
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
