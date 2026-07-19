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
) -> dict[str, Any]:
    """Latest quote for every (source, asset, currency) with bid/ask, filterable."""
    rows = await price_data.latest_prices(
        session, source=source, asset=asset, currency=currency, type=type
    )
    items = [
        {
            "source": r["source_slug"],
            "source_role": r["source_role"],
            "asset": r["asset_slug"],
            "asset_symbol": r["asset_symbol"],
            "asset_type": r["asset_type"],
            "unit": r["asset_unit"],
            "currency": r["currency_code"],
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
