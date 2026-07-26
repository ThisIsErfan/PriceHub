"""SEO partner data logic.

The SEO team publishes price/news content, so this module serves clean,
headline-friendly shapes: the newest price per asset (platform quotes only, no
per-source noise) and recent metals news. It reads through the shared data helpers
so the SQL stays correct and in one place.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.data import news as news_data
from app.shared.data import prices as price_data
from app.shared.data import seo_prices as seo_data

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


# --- SEO price page (seo_schm.talasea_gold_prices, 18k from gerami) ----------

# Exactly the display fields the price page needs — the columns of
# seo_schm.talasea_gold_prices (internal id/raw_data/timestamps excluded).
_PAGE_FIELDS = (
    "category", "slug", "name", "unit",
    "current_price", "low_price", "high_price",
    "change_1d_percent", "change_30d_percent",
    "weekly_chart_path", "detail_url", "crawled_at",
)

# The 18k-gram row (طلای ۱۸ عیار) whose numeric fields come from the gerami
# source instead of the talasea scrape.
_GERAMI_ROW_SLUG = "geram18"


def _pct(current: Any, past: Any) -> Optional[Decimal]:
    """Percentage change from `past` to `current`, to 3 dp (talasea's precision)."""
    if current is None or past is None or Decimal(past) == 0:
        return None
    return ((Decimal(current) - Decimal(past)) / Decimal(past) * Decimal(100)).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )


async def price_page(session: AsyncSession) -> dict[str, Any]:
    """The site's price page: every row of seo_schm.talasea_gold_prices, with the
    18k-gram row's numeric fields rebuilt from the GERAMI source.

    All rows keep the talasea-scraped fields. For `geram18`, the fields gerami
    can rebuild from its own price history — current price, day low/high, and
    1-day / 30-day change — are overridden; the row's name/unit/detail_url and
    the weekly sparkline (a talasea render, absent from the gerami feed) are kept
    from the stored row. If gerami has no history, the stored talasea values are
    served unchanged.
    """
    rows = await seo_data.talasea_gold_prices(session)

    gerami = await seo_data.gerami_gold_18k(session)
    g_fields: Optional[dict[str, Any]] = None
    if gerami is not None:
        g_fields = {
            "current_price":      gerami.get("current_price"),
            "low_price":          gerami.get("low_price"),
            "high_price":         gerami.get("high_price"),
            "change_1d_percent":  _pct(gerami.get("current_price"), gerami.get("price_1d_ago")),
            "change_30d_percent": _pct(gerami.get("current_price"), gerami.get("price_30d_ago")),
            "crawled_at":         gerami.get("crawled_at"),
        }

    items: list[dict[str, Any]] = []
    gerami_applied = False
    for r in rows:
        item = {k: r.get(k) for k in _PAGE_FIELDS}
        if r["slug"] == _GERAMI_ROW_SLUG and g_fields is not None:
            # Override only the fields gerami actually rebuilt (skip None so a
            # gap in gerami's history never blanks a field the scrape had).
            for key, value in g_fields.items():
                if value is not None:
                    item[key] = value
            gerami_applied = True
        items.append(item)

    return {
        "items": items,
        "count": len(items),
        "gold_18k_source": "gerami" if gerami_applied else "talasea",
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
