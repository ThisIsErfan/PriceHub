"""Technical partner data logic.

The technical team integrates raw data into their own systems, so this module
exposes fuller rows than the SEO feed — every source, bid/ask, and supplier
buy/sell quotes — straight from the shared data helpers with minimal reshaping.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.data import prices as price_data


def _money(x: Any) -> Optional[str]:
    """Quantize a numeric to 2 dp and return it as a string (matches the price
    fields elsewhere in the feed). None stays None."""
    if x is None:
        return None
    return str(Decimal(str(round(float(x), 2))))


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


async def price_stats(
    session: AsyncSession,
    *,
    asset: str,
    currency: str,
    max_age_seconds: int = 180,
    role: Optional[str] = None,
) -> dict[str, Any]:
    """Cross-source statistical summary for one (asset, currency).

    Computed over each source's clean `mid` (canonical comparable price, matching
    the copilot consensus). Sources whose latest sample is older than
    `max_age_seconds` (default 180s — we crawl every 120s, so >3min = stale) are
    EXCLUDED, as are sources with no usable price. Gerami's own current quote is
    always surfaced separately for reference.
    """
    rows = await price_data.latest_clean_for_stats(
        session, asset=asset, currency=currency, role=role
    )

    params = {"max_age_seconds": max_age_seconds, "role": role}
    if not rows:
        return {
            "asset": {"slug": asset},
            "currency": {"code": currency},
            "as_of": None,
            "params": params,
            "sample": {"total_sources": 0, "included": 0, "excluded": 0,
                       "included_sources": [], "excluded_sources": []},
            "stats": None,
            "gerami": None,
            "message": "no data for this asset/currency",
        }

    first = rows[0]
    asset_meta = {
        "slug": first["asset_slug"], "symbol": first["asset_symbol"],
        "title_fa": first["asset_title_fa"], "unit": first["asset_unit"],
    }
    currency_meta = {"code": first["currency_code"], "title_fa": first["currency_title_fa"]}

    # Split into the fresh, usable sample vs everything excluded (stale or no price).
    included, excluded = [], []
    for r in rows:
        usable = r["mid"] is not None and float(r["mid"]) > 0
        fresh = r["age_seconds"] is not None and r["age_seconds"] <= max_age_seconds
        if usable and fresh:
            included.append(r)
        else:
            reason = "no_price" if not usable else "stale"
            excluded.append({
                "slug": r["source_slug"],
                "age_seconds": int(round(r["age_seconds"])) if r["age_seconds"] is not None else None,
                "reason": reason,
            })

    vals = [float(r["mid"]) for r in included]
    stats = None
    mean = median = None
    if vals:
        mean = statistics.fmean(vals)
        median = statistics.median(vals)
        std = statistics.pstdev(vals) if len(vals) > 1 else 0.0

        def trimmed_mean(k: float):
            # Keep values within k standard deviations of the mean, then re-average.
            if std == 0:
                return mean, len(vals)
            kept = [v for v in vals if abs(v - mean) <= k * std]
            return (statistics.fmean(kept), len(kept)) if kept else (None, 0)

        m2, c2 = trimmed_mean(2)
        m3, c3 = trimmed_mean(3)
        stats = {
            "min": _money(min(vals)),
            "max": _money(max(vals)),
            "mean": _money(mean),
            "median": _money(median),
            "stdev": _money(std),
            "mean_2sigma": _money(m2),
            "count_2sigma": c2,
            "mean_3sigma": _money(m3),
            "count_3sigma": c3,
        }

    included_slugs = {r["source_slug"] for r in included}

    # Gerami's own current quote — always shown, even if it was excluded above.
    gerami = None
    grow = next((r for r in rows if r["source_slug"] == "gerami"), None)
    if grow is not None:
        gmid = float(grow["mid"]) if grow["mid"] is not None else None
        in_stats = "gerami" in included_slugs
        gerami = {
            "price": _money(grow["price"]) if (grow["price"] is not None and float(grow["price"]) > 0) else None,
            "bid": _money(grow["bid"]),
            "ask": _money(grow["ask"]),
            "mid": _money(gmid),
            "crawled_at": grow["crawled_at"],
            "age_seconds": int(round(grow["age_seconds"])) if grow["age_seconds"] is not None else None,
            "included_in_stats": in_stats,
            "diff_from_median": _money(gmid - median) if (median is not None and gmid is not None) else None,
            "diff_from_mean": _money(gmid - mean) if (mean is not None and gmid is not None) else None,
        }

    as_of = max((r["crawled_at"] for r in included), default=None) or max(r["crawled_at"] for r in rows)

    return {
        "asset": asset_meta,
        "currency": currency_meta,
        "as_of": as_of,
        "params": params,
        "sample": {
            "total_sources": len(rows),
            "included": len(included),
            "excluded": len(excluded),
            "included_sources": sorted(included_slugs),
            "excluded_sources": excluded,
        },
        "stats": stats,
        "gerami": gerami,
    }
