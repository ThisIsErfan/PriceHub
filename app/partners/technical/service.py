"""Technical partner data logic.

The technical team integrates raw data into their own systems, so this module
exposes fuller rows than the SEO feed — every source, bid/ask, and supplier
buy/sell quotes — straight from the shared data helpers with minimal reshaping.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.data import prices as price_data


async def all_latest_prices(
    session: AsyncSession,
    *,
    source: Optional[str] = None,
    asset: Optional[str] = None,
    currency: Optional[str] = None,
    type: Optional[str] = None,
    assets: Optional[str] = None,
) -> dict[str, Any]:
    """Latest quote per (source, asset, currency) — same shape as the copilot
    `GET /api/v1/prices/latest` (the "platform compare" section): nested
    source/asset/currency refs, `is_single_rate`, and price/bid/ask.
    """
    rows = await price_data.latest_prices(
        session, source=source, asset=asset, currency=currency, type=type, assets=assets
    )
    items = [
        {
            "source": {
                "slug": r["source_slug"],
                "title_en": r["source_title_en"],
                "title_fa": r["source_title_fa"],
            },
            "asset": {
                "slug": r["asset_slug"],
                "symbol": r["asset_symbol"],
                "title_fa": r["asset_title_fa"],
                "unit": r["asset_unit"],
            },
            "currency": {
                "code": r["currency_code"],
                "title_fa": r["currency_title_fa"],
            },
            "is_single_rate": r["is_single_rate"],
            "price": r["price"],
            "bid": r["bid"],
            "ask": r["ask"],
            "crawled_at": r["crawled_at"],
        }
        for r in rows
    ]
    return {
        "items": items,
        "count": len(items),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def supplier_latest(
    session: AsyncSession, *, source: Optional[str] = None, asset: Optional[str] = None
) -> dict[str, Any]:
    """Latest supplier buy/sell quotes."""
    rows = await price_data.latest_supplier_prices(session, source=source, asset=asset)
    items = [
        {
            "supplier": r["source_slug"],
            "supplier_title_fa": r["source_title_fa"],
            "asset": r["asset_slug"],
            "unit": r["asset_unit"],
            "currency": r["currency_code"],
            "buy_price": r["buy_price"],
            "sell_price": r["sell_price"],
            "mid_price": r["mid_price"],
            "crawled_at": r["crawled_at"],
        }
        for r in rows
    ]
    return {"items": items, "count": len(items)}
