"""Reports partner endpoints — mounted at /v1/reports by app.main.

Reporting (not operational) data for senior management, consumed by an Airflow
DAG that posts it to a private Telegram channel every 2 minutes. All GET; require
an ACTIVE key scoped to the `reports` partner.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_partner
from app.db.session import get_session
from app.partners.reports import service
from app.shared.schemas import ok

SLUG = "reports"
router = APIRouter(tags=["reports"])

_auth = Depends(require_partner(SLUG, scope="reports:read"))


@router.get(
    "/platform-compare",
    summary="Competitive report: Gerami vs platforms by user-buy price + market stats + Persian message",
)
async def platform_compare(
    _ctx=_auth,
    asset: str = Query(..., description="Asset slug: gold-18k | silver-999 | copper (required)"),
    currency: str = Query("IRT", description="Currency code (default IRT)"),
    max_age_seconds: int = Query(
        180, ge=30, le=3600,
        description="Exclude sources not updated within this many seconds (default 180 = 3min)",
    ),
    exclude: Optional[str] = Query(
        None, description="Comma-separated source slugs to drop, e.g. talair_api"
    ),
    session: AsyncSession = Depends(get_session),
):
    return ok(
        await service.platform_report(
            session, asset=asset, currency=currency,
            max_age_seconds=max_age_seconds,
            exclude=exclude.split(",") if exclude else None,
        )
    )
