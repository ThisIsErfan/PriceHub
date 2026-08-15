"""The response standard: entity refs, quote items, and the list wrapper.

One rule for the whole API — wherever a response names a **source**, an **asset**
or a **currency**, it embeds the SAME nested object with the SAME keys. Never a
flattened `asset_title_fa`, never a partial subset that differs per endpoint.
Endpoints may differ in their *value* fields (bid/ask, statistics, page columns);
they never differ in how an entity is spelled.

Every key is always present: an unknown value is ``null``, not an absent key, so
a consumer can rely on one fixed shape.

    source   {slug, title_fa, title_en, role}                 role: platform|reference|supplier
    asset    {slug, symbol, title_fa, title_en, type, unit}    symbol: the STANDARD code
    currency {slug, code, symbol, title_fa, title_en, type}    type: fiat|crypto

`asset.slug` and `currency.slug` are the two input keys — both lowercase, so a
query string never mixes cases (``?asset=gold-18k&currency=irt``).

The helpers read a row straight from the shared queries in ``app.shared.data``,
which name their columns ``source_slug`` / ``asset_title_fa`` / ``currency_code``
— hence the prefix argument. Catalog queries whose columns are already bare
(``slug``, ``title_fa``, …) pass ``prefix=""``.

Keeping the standard in one module is what stops the drift this replaces: an
endpoint cannot invent its own half-version of a ref without editing this file.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional


def source_ref(row: Mapping[str, Any], *, prefix: str = "source_") -> dict[str, Any]:
    """The canonical price-source object (`sources` catalog)."""
    return {
        "slug": row.get(f"{prefix}slug"),
        "title_fa": row.get(f"{prefix}title_fa"),
        "title_en": row.get(f"{prefix}title_en"),
        "role": row.get(f"{prefix}role"),
    }


def asset_ref(row: Mapping[str, Any], *, prefix: str = "asset_") -> dict[str, Any]:
    """The canonical asset object (`assets` catalog).

    `slug` is the input key everywhere (`?asset=gold-18k`); `symbol` is the
    STANDARD instrument code carrying purity and unit (`XAU750g`, `XAG999g`,
    `XCU9999g`) — i.e. the DB's `assets.std_symbol`, not the internal join key.
    There is no separate `std_symbol` field: the standard code IS the symbol a
    partner sees.

    Assets for which no standard code has been agreed yet (24K, melted, ounces,
    coins, currencies) have `std_symbol` NULL in the catalog; rather than
    reporting `symbol: null` for them, we fall back to the internal code
    (`GOLD_24K`) so the field is always a usable identifier.
    """
    return {
        "slug": row.get(f"{prefix}slug"),
        "symbol": row.get(f"{prefix}std_symbol") or row.get(f"{prefix}symbol"),
        "title_fa": row.get(f"{prefix}title_fa"),
        "title_en": row.get(f"{prefix}title_en"),
        "type": row.get(f"{prefix}type"),
        "unit": row.get(f"{prefix}unit"),
    }


def currency_ref(row: Mapping[str, Any], *, prefix: str = "currency_") -> dict[str, Any]:
    """The canonical currency object (`currencies` catalog).

    `slug` is the input key (`?currency=irt`) — the lowercase form of `code`,
    mirroring `asset.slug`; `code` is the standard currency code the quote is
    denominated in (`IRT`, `IRR`, `USD`); `symbol` is its display sign (`تومان`,
    `﷼`, `$`), `null` when the catalog has none; `type` is its class
    (`fiat` | `crypto`).
    """
    return {
        "slug": row.get(f"{prefix}slug"),
        "code": row.get(f"{prefix}code"),
        "symbol": row.get(f"{prefix}symbol"),
        "title_fa": row.get(f"{prefix}title_fa"),
        "title_en": row.get(f"{prefix}title_en"),
        "type": row.get(f"{prefix}type"),
    }


def news_source_ref(row: Mapping[str, Any], *, prefix: str = "source_") -> dict[str, Any]:
    """The canonical news-source object (`news_schm.news_sources` — a separate
    catalog from price sources, so it carries the feed `type`
    (website|website_api|rss) where a price source carries `role`)."""
    return {
        "slug": row.get(f"{prefix}slug"),
        "title_fa": row.get(f"{prefix}title_fa"),
        "title_en": row.get(f"{prefix}title_en"),
        "type": row.get(f"{prefix}type"),
    }


def quote_item(
    row: Mapping[str, Any],
    *,
    bid: Any,
    ask: Any,
    is_single_rate: Optional[bool],
) -> dict[str, Any]:
    """One priced row of any feed — platform or supplier — in the standard shape.

    `bid` is خرید (the source buys), `ask` is فروش (the source sells). There is
    no bare `price`: a single-rate source's one number is reported as
    `bid == ask` with `is_single_rate: true`.
    """
    return {
        "source": source_ref(row),
        "asset": asset_ref(row),
        "currency": currency_ref(row),
        "is_single_rate": is_single_rate,
        "bid": bid,
        "ask": ask,
        "crawled_at": row.get("crawled_at"),
    }


def listing(items: list[Any], **meta: Any) -> dict[str, Any]:
    """The `data` block of every list endpoint: items + count + generated_at.

    Endpoint-specific metadata is passed as kwargs and sits between `count` and
    `generated_at` (e.g. `gold_18k_source` on the SEO price page).
    """
    return {
        "items": items,
        "count": len(items),
        **meta,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
