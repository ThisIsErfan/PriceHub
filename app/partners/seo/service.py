"""SEO partner data logic.

The SEO team publishes price/news content, so this module serves a focused feed:
the newest quote for the assets they write about (platform quotes only, no
supplier noise), the site's price page, and recent metals news. It reads through
the shared data helpers so the SQL stays correct and in one place.

The items themselves follow the same standard as every other partner — the refs
and list wrapper come from `app.shared.refs`, so an `asset` here is byte-for-byte
the `asset` the technical feed returns.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.data import news as news_data
from app.shared.data import prices as price_data
from app.shared.data import seo_prices as seo_data
from app.shared.refs import listing, news_source_ref, quote_item, source_ref

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


def _pos(v: Any) -> bool:
    """A usable quote: present and > 0 (drops null and the `-1` sentinel)."""
    return v is not None and float(v) > 0


def _seo_item(r: dict[str, Any]) -> dict[str, Any]:
    """One featured price in the standard quote shape.

    Most SEO sources publish a single number rather than a buy/sell split, so it
    is reported as `bid == ask` — the same rule the technical feed follows. For
    display, read `ask` (فروش).
    """
    price = r["price"] if _pos(r["price"]) else None
    bid = r["bid"] if _pos(r["bid"]) else price
    ask = r["ask"] if _pos(r["ask"]) else price
    return quote_item(r, bid=bid, ask=ask, is_single_rate=r["is_single_rate"])


async def featured_prices(
    session: AsyncSession, *, asset: Optional[str] = None
) -> dict[str, Any]:
    """Latest platform price for each featured asset (or one asset if given)."""
    rows = await price_data.latest_prices(session, asset=asset)
    allowed = {asset} if asset else set(SEO_FEATURED_ASSETS)
    items = [
        _seo_item(r)
        for r in rows
        if r["asset_slug"] in allowed and r["source_role"] != "supplier"
    ]
    return listing(items)


# --- SEO price page (seo_schm.talasea_gold_prices, 18k from gerami) ----------

# Exactly the display fields the price page needs — the columns of
# seo_schm.talasea_gold_prices (internal id/raw_data/timestamps excluded).
_PAGE_FIELDS = (
    "category", "slug", "name", "unit",
    "current_price", "low_price", "high_price",
    "change_1d_percent", "change_30d_percent",
    "weekly_chart_path", "crawled_at",
)

# The 18k-gram row (طلای ۱۸ عیار) whose numeric fields come from the gerami
# source instead of the talasea scrape.
_GERAMI_ROW_SLUG = "geram18"

# Who produced a page row. Both are real rows of the `sources` catalog, so the
# per-item `source` ref is built from the catalog rather than hard-coded titles.
_PAGE_SOURCE = "talasea"
_GERAMI_SOURCE = "gerami"


async def _page_source_refs(session: AsyncSession) -> dict[str, dict[str, Any]]:
    """`source` refs for the two producers of a price-page row, by slug.

    A source missing from the catalog still yields a full ref (slug set, the rest
    null) so the item shape never varies.
    """
    wanted = {_PAGE_SOURCE, _GERAMI_SOURCE}
    catalog = {
        r["slug"]: source_ref(r, prefix="")
        for r in await price_data.list_sources(session)
        if r["slug"] in wanted
    }
    return {slug: catalog.get(slug, source_ref({"source_slug": slug})) for slug in wanted}


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
    1-day / 30-day change — are overridden; the row's name/unit and the weekly
    sparkline (a talasea render, absent from the gerami feed) are kept from the
    stored row. If gerami has no history, the stored talasea values are served
    unchanged.

    Each item carries the standard `source` ref naming which producer it came
    from. Its own `category`/`slug`/`name`/`unit` stay as-is: these are the
    scraped page's own columns, not rows of the `assets`/`currencies` catalogs,
    so there is no asset or currency ref to attach.
    """
    rows = await seo_data.talasea_gold_prices(session)
    page_sources = await _page_source_refs(session)

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
        item = {"source": page_sources[_PAGE_SOURCE], **{k: r.get(k) for k in _PAGE_FIELDS}}
        if r["slug"] == _GERAMI_ROW_SLUG and g_fields is not None:
            # Override only the fields gerami actually rebuilt (skip None so a
            # gap in gerami's history never blanks a field the scrape had).
            for key, value in g_fields.items():
                if value is not None:
                    item[key] = value
            item["source"] = page_sources[_GERAMI_SOURCE]
            gerami_applied = True
        items.append(item)

    return listing(
        items,
        gold_18k_source=_GERAMI_SOURCE if gerami_applied else _PAGE_SOURCE,
    )


async def recent_news(
    session: AsyncSession, *, symbol: Optional[str] = None, limit: int = 20
) -> dict[str, Any]:
    """Recent metals news headlines (title/summary/link/published_at)."""
    limit = max(1, min(limit, 50))  # hard ceiling
    rows = await news_data.latest_news(session, symbol=symbol, limit=limit)
    items = [
        {
            "source": news_source_ref(r),
            "title": r["title"],
            "summary": r["summary"],
            "url": r["url"],
            "publisher": r["publisher"],
            "image_url": r["image_url"],
            "published_at": r["published_at"],
        }
        for r in rows
    ]
    return listing(items)
