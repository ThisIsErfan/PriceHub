"""Technical partner data logic.

The technical team integrates raw data into their own systems, so this module
exposes fuller rows than the SEO feed — every source, bid/ask, and supplier
buy/sell quotes — straight from the shared data helpers with minimal reshaping.

Every response is built through `app.shared.refs`, so platform rows, supplier
rows and the stats header all spell a source/asset/currency the same way.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.data import prices as price_data
from app.shared.refs import asset_ref, currency_ref, listing, quote_item
from app.shared.stats import money as _money
from app.shared.stats import side_stats as _side_stats


def _pos(v: Any) -> bool:
    """A usable quote: present and > 0 (drops null and the `-1` sentinel)."""
    return v is not None and float(v) > 0


def _bid_ask(row: dict[str, Any]) -> tuple[Any, Any]:
    """(bid, ask) for a row. A single-rate source quotes one number that stands
    for both sides, so we fall its `price` into both `bid` and `ask` — the feed
    always exposes bid/ask and never a bare `price`."""
    price = row["price"] if _pos(row["price"]) else None
    bid = row["bid"] if _pos(row["bid"]) else price
    ask = row["ask"] if _pos(row["ask"]) else price
    return bid, ask


async def all_latest_prices(
    session: AsyncSession,
    *,
    source: Optional[str] = None,
    asset: Optional[str] = None,
    currency: Optional[str] = None,
    type: Optional[str] = None,
    assets: Optional[str] = None,
) -> dict[str, Any]:
    """Latest quote per (source, asset, currency) — nested source/asset/currency
    refs, `is_single_rate`, and `bid`/`ask`. There is no bare `price`: a
    single-rate source's single number is surfaced as `bid == ask`.
    """
    rows = await price_data.latest_prices(
        session, source=source, asset=asset, currency=currency, type=type, assets=assets
    )
    items = []
    for r in rows:
        bid, ask = _bid_ask(r)
        items.append(
            quote_item(r, bid=bid, ask=ask, is_single_rate=r["is_single_rate"])
        )
    return listing(items)


async def supplier_latest(
    session: AsyncSession, *, source: Optional[str] = None, asset: Optional[str] = None
) -> dict[str, Any]:
    """Latest supplier quotes, in the same item shape as the platform feed.

    A supplier's `buy_price` (خرید — the supplier buys) is the `bid` and its
    `sell_price` (فروش — the supplier sells) is the `ask`, exactly the sides the
    platform feed uses, so one parser reads both feeds; `source.role` is what
    tells them apart. Suppliers always quote two sides, hence
    `is_single_rate: false`.
    """
    rows = await price_data.latest_supplier_prices(session, source=source, asset=asset)
    items = [
        quote_item(
            r,
            bid=r["buy_price"] if _pos(r["buy_price"]) else None,
            ask=r["sell_price"] if _pos(r["sell_price"]) else None,
            is_single_rate=False,
        )
        for r in rows
    ]
    return listing(items)


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
        # Nothing matched, so there is no catalog row to describe the asset or
        # currency — the refs keep their full key set with null values rather
        # than shrinking to the slug the caller passed.
        return {
            "asset": asset_ref({"asset_slug": asset}),
            "currency": currency_ref({"currency_code": currency}),
            "as_of": None,
            "params": params,
            "sample": {"total_sources": 0, "included": 0, "excluded": 0,
                       "included_sources": [], "excluded_sources": []},
            "stats": None,
            "gerami": None,
            "message": "no data for this asset/currency",
        }

    first = rows[0]
    asset_meta = asset_ref(first)
    currency_meta = currency_ref(first)

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
