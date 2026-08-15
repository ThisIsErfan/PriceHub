"""Reports partner data logic.

Builds the competitive "where does Gerami stand" report for one (asset,
currency): a leaderboard of platforms by **user buy price** (the platform's
sell/ask price, فروش) high→low, market summary stats (excluding Gerami), and
Gerami's own position — plus a ready-to-post Persian Telegram message under
`message`. Consumed by an Airflow DAG that posts it to the private channel.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.partners.reports import format as fmt
from app.shared.data import prices as price_data
from app.shared.refs import asset_ref, currency_ref
from app.shared.stats import money, side_stats

GERAMI = "gerami"


def _ask(r: dict[str, Any]) -> Optional[float]:
    """A source's clean user-buy price (ask/فروش), or None if unusable."""
    v = r["ask_clean"]
    return float(v) if (v is not None and float(v) > 0) else None


async def platform_report(
    session: AsyncSession,
    *,
    asset: str,
    currency: str = "IRT",
    max_age_seconds: int = 180,
    exclude: Optional[list[str]] = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    rows = await price_data.latest_clean_for_stats(
        session, asset=asset, currency=currency, role=None
    )
    # Drop explicitly excluded sources (e.g. talair_api on gold) before anything.
    if exclude:
        drop = {e.strip() for e in exclude if e.strip()}
        rows = [r for r in rows if r["source_slug"] not in drop]

    params = {"max_age_seconds": max_age_seconds, "sort_by": "user_buy_price (ask/فروش)"}
    # Same asset/currency refs as every other partner endpoint. With no matching
    # row there is no catalog data to describe them, so the refs keep their full
    # key set with null values rather than shrinking to the slug/code passed in.
    base = {
        "asset": asset_ref({"asset_slug": asset}),
        "currency": currency_ref({"currency_code": currency}),
        "params": params,
    }

    if not rows:
        stub = {"asset": base["asset"], "gerami": None, "market": None,
                "leaderboard": [], "stamp_fa": fmt.tehran_stamp(now)}
        return {**base, "as_of": None, "gerami": None, "market": None,
                "leaderboard": [], "stamp_fa": stub["stamp_fa"],
                "message": fmt.build_message(stub, now),
                "message_compact": fmt.build_compact(stub),
                "message_table": fmt.build_table(stub),
                "note": "no data for this asset/currency"}

    first = rows[0]
    asset_meta = asset_ref(first)
    currency_meta = currency_ref(first)

    # Fresh, usable-for-buy-price sources make up the leaderboard; stale/no-price
    # are noted separately.
    fresh, stale = [], []
    for r in rows:
        ask = _ask(r)
        is_fresh = r["age_seconds"] is not None and r["age_seconds"] <= max_age_seconds
        if ask is not None and is_fresh:
            fresh.append(r)
        else:
            stale.append({
                "slug": r["source_slug"], "source_fa": r["source_title_fa"],
                "age_seconds": int(round(r["age_seconds"])) if r["age_seconds"] is not None else None,
                "reason": "no_price" if ask is None else "stale",
            })

    # Leaderboard: every fresh source (incl. Gerami) by user-buy price, high→low.
    lb_rows = sorted(fresh, key=lambda r: _ask(r), reverse=True)
    grow = next((r for r in fresh if r["source_slug"] == GERAMI), None)
    gerami_ask = _ask(grow) if grow is not None else None

    def _bid(r):  # user-sell price (platform buy / bid, خرید)
        v = r["bid_clean"]
        return float(v) if (v is not None and float(v) > 0) else None

    leaderboard = []
    for i, r in enumerate(lb_rows, start=1):
        is_g = r["source_slug"] == GERAMI
        diff = None if (is_g or gerami_ask is None) else money(_ask(r) - gerami_ask)
        leaderboard.append({
            "rank": i,
            "source": r["source_slug"],
            "source_fa": r["source_title_fa"],
            "source_en": r["source_title_en"],
            # User-side prices (what the customer sees):
            "user_buy_price": money(_ask(r)),   # user BUYS at the platform's sell/ask (فروش)
            "user_sell_price": money(_bid(r)),  # user SELLS at the platform's buy/bid (خرید)
            "spread": money(_ask(r) - _bid(r)) if (_ask(r) is not None and _bid(r) is not None) else None,
            "diff_from_gerami": diff,
            "is_gerami": is_g,
        })

    # Market stats over the COMPETITORS' user-buy price (Gerami excluded).
    competitors = [r for r in fresh if r["source_slug"] != GERAMI]
    ask_vals = [_ask(r) for r in competitors]
    block, mean, median = side_stats(ask_vals)
    market = None
    if block is not None:
        lo = min(competitors, key=lambda r: _ask(r))
        hi = max(competitors, key=lambda r: _ask(r))
        market = {
            "count": len(competitors),
            "mean": block["mean"], "median": block["median"], "stdev": block["stdev"],
            "mean_2sigma": block["mean_2sigma"], "count_2sigma": block["count_2sigma"],
            "mean_3sigma": block["mean_3sigma"], "count_3sigma": block["count_3sigma"],
            "min": {"price": money(_ask(lo)), "source": lo["source_slug"], "source_fa": lo["source_title_fa"]},
            "max": {"price": money(_ask(hi)), "source": hi["source_slug"], "source_fa": hi["source_title_fa"]},
            "spread": money(_ask(hi) - _ask(lo)),
            "excluded_stale": stale,
        }

    # Gerami's position within the leaderboard + vs the market.
    gerami = None
    if grow is not None:
        rank = next(row["rank"] for row in leaderboard if row["is_gerami"])
        total = len(leaderboard)
        n_comp = total - 1
        more_expensive = rank - 1          # platforms above Gerami (dearer for the buyer)
        cheaper_pct = round(more_expensive / n_comp * 100) if n_comp > 0 else 0
        position = "cheaper" if (mean is not None and gerami_ask < mean) else "more_expensive"
        gerami = {
            "present": True,
            "rank": rank,
            "of": total,
            "user_buy_price": money(gerami_ask),
            "cheaper_than_competitors": more_expensive,
            "competitors": n_comp,
            "cheaper_than_pct": cheaper_pct,
            "position": position,
            "vs_market": {
                "diff_from_mean": money(gerami_ask - mean) if mean is not None else None,
                "diff_pct_from_mean": round((gerami_ask - mean) / mean * 100, 2) if mean else None,
                "diff_from_median": money(gerami_ask - median) if median is not None else None,
            },
            "vs_cheapest": money(gerami_ask - _ask(lo)) if market else None,
            "vs_most_expensive": money(gerami_ask - _ask(hi)) if market else None,
            "crawled_at": grow["crawled_at"],
            "age_seconds": int(round(grow["age_seconds"])) if grow["age_seconds"] is not None else None,
        }
    else:
        gerami = {"present": False}

    as_of = max((r["crawled_at"] for r in fresh), default=None) or max(r["crawled_at"] for r in rows)

    report = {
        **base,
        "asset": asset_meta,
        "currency": currency_meta,
        "as_of": as_of,
        "gerami": gerami,
        "market": market,
        "leaderboard": leaderboard,
        "stamp_fa": fmt.tehran_stamp(now),
    }
    report["message"] = fmt.build_message(report, now)
    report["message_compact"] = fmt.build_compact(report)
    report["message_table"] = fmt.build_table(report)
    return report
