"""SEO partner data logic.

The SEO team publishes price/news content, so this module serves clean,
headline-friendly shapes: the newest price per asset (platform quotes only, no
per-source noise) and recent metals news. It reads through the shared data helpers
so the SQL stays correct and in one place.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.data import news as news_data
from app.shared.data import prices as price_data

# The assets the SEO team writes about most; keeps their feed focused.
SEO_FEATURED_ASSETS = [
    "gold-18k",
    "gold-24k",
    "gold-melted",
    "gold-ounce",
    "silver-999",
    "silver-ounce",
    "coin-emami",
    "coin-bahar",
    "coin-half",
    "coin-quarter",
]


def _slim_price(r: dict[str, Any]) -> dict[str, Any]:
    """Reduce a raw price row to the fields SEO content needs."""
    return {
        "asset": r["asset_slug"],
        "asset_title_fa": r["asset_title_fa"],
        "asset_title_en": r["asset_title_en"],
        "unit": r["asset_unit"],
        "source": r["source_slug"],
        "currency": r["currency_code"],
        "price": r["price"],
        "crawled_at": r["crawled_at"],
    }


async def featured_prices(
    session: AsyncSession, *, asset: Optional[str] = None
) -> dict[str, Any]:
    """Latest platform price for each featured asset (or one asset if given)."""
    rows = await price_data.latest_prices(session, asset=asset)
    allowed = {asset} if asset else set(SEO_FEATURED_ASSETS)
    items = [
        _slim_price(r)
        for r in rows
        if r["asset_slug"] in allowed and r["source_role"] != "supplier"
    ]
    return {
        "items": items,
        "count": len(items),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def recent_news(
    session: AsyncSession, *, symbol: Optional[str] = None, limit: int = 20
) -> dict[str, Any]:
    """Recent metals news headlines (title/summary/link/published_at)."""
    limit = max(1, min(limit, 50))  # hard ceiling
    rows = await news_data.latest_news(session, symbol=symbol, limit=limit)
    items = [
        {
            "title": r["title"],
            "summary": r["summary"],
            "url": r["url"],
            "publisher": r["publisher"],
            "image_url": r["image_url"],
            "published_at": r["published_at"],
            "source": r["source_slug"],
        }
        for r in rows
    ]
    return {"items": items, "count": len(items)}
