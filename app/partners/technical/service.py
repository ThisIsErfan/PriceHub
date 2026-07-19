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


def _side_stats(vals: list[float]) -> tuple[Optional[dict[str, Any]], Optional[float], Optional[float]]:
    """Summary stats for one side (bid or ask). Returns (block, mean, median);
    block is None when there are no values. `mean_Nsigma` drops values beyond
    ±Nσ of the mean, then re-averages (single-pass sigma clip)."""
    if not vals:
        return None, None, None
    mean = statistics.fmean(vals)
    median = statistics.median(vals)
    std = statistics.pstdev(vals) if len(vals) > 1 else 0.0

    def trimmed_mean(k: float):
        if std == 0:
            return mean, len(vals)
        kept = [v for v in vals if abs(v - mean) <= k * std]
        return (statistics.fmean(kept), len(kept)) if kept else (None, 0)

    m2, c2 = trimmed_mean(2)
    m3, c3 = trimmed_mean(3)
    block = {
        "sample_count": len(vals),
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
    return block, mean, median


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
    """Cross-source statistical summary for one (asset, currency), computed
    SEPARATELY for bid (خرید) and ask (فروش) — each over its own per-source data.

    Each source contributes a clean bid and ask (the "-1" sentinel is stripped;
    a single-rate source's price counts as both sides). Sources whose latest
    sample is older than `max_age_seconds` (default 180s — we crawl every 120s,
    so >3min = stale) are EXCLUDED, as are sources with no usable quote. Gerami is
    excluded from the stats and surfaced separately for reference.
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

    # Gerami is handled separately and is deliberately NOT part of the market
    # statistics — pull it out before building the sample.
    grow = next((r for r in rows if r["source_slug"] == "gerami"), None)
    sample_rows = [r for r in rows if r["source_slug"] != "gerami"]

    def _side(r, col):  # usable clean value for a side, or None
        v = r[col]
        return float(v) if (v is not None and float(v) > 0) else None

    # Split the (non-gerami) sample into fresh+usable vs excluded (stale/no quote).
    included, excluded = [], []
    for r in sample_rows:
        usable = _side(r, "bid_clean") is not None or _side(r, "ask_clean") is not None
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

    # Separate stats per side, each over its own per-source values.
    bid_vals = [v for r in included if (v := _side(r, "bid_clean")) is not None]
    ask_vals = [v for r in included if (v := _side(r, "ask_clean")) is not None]
    bid_block, bid_mean, bid_median = _side_stats(bid_vals)
    ask_block, ask_mean, ask_median = _side_stats(ask_vals)
    stats = {"bid": bid_block, "ask": ask_block}

    included_slugs = {r["source_slug"] for r in included}

    # Gerami's own current quote — shown separately, NEVER counted in the stats.
    # Its bid/ask are compared to the market's bid/ask stats respectively.
    gerami = None
    if grow is not None:
        gprice = _side(grow, "price") if "price" in grow else None
        gbid = _side(grow, "bid_clean")
        gask = _side(grow, "ask_clean")
        gerami = {
            "price": _money(gprice),
            "bid": _money(grow["bid"]),
            "ask": _money(grow["ask"]),
            "crawled_at": grow["crawled_at"],
            "age_seconds": int(round(grow["age_seconds"])) if grow["age_seconds"] is not None else None,
            "bid_vs_market": {
                "diff_from_median": _money(gbid - bid_median) if (bid_median is not None and gbid is not None) else None,
                "diff_from_mean": _money(gbid - bid_mean) if (bid_mean is not None and gbid is not None) else None,
            },
            "ask_vs_market": {
                "diff_from_median": _money(gask - ask_median) if (ask_median is not None and gask is not None) else None,
                "diff_from_mean": _money(gask - ask_mean) if (ask_mean is not None and gask is not None) else None,
            },
        }

    as_of = max((r["crawled_at"] for r in included), default=None) or max(r["crawled_at"] for r in rows)

    return {
        "asset": asset_meta,
        "currency": currency_meta,
        "as_of": as_of,
        "params": params,
        "sample": {
            "total_sources": len(sample_rows),
            "included": len(included),
            "excluded": len(excluded),
            "included_sources": sorted(included_slugs),
            "excluded_sources": excluded,
        },
        "stats": stats,
        "gerami": gerami,
    }
