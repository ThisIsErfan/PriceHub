"""Reusable read queries over the price schema (``price_schm``).

Partner modules call these instead of writing their own SQL, so every partner
reads prices the same, correct way. All queries run as ``partner_api_usr``
(SELECT only). Returns plain dicts (JSON-ready) — each partner module decides
what subset/shape to expose.

Faithful to how the copilot backend reads the same tables:
  * latest quotes come from the ``price_latest`` mirror (one row per
    source/asset/currency, kept current in place by the crawler) — constant-time
    regardless of history size.
  * supplier quotes come from ``supplier_price_latest`` (same idea).
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# --- Latest platform/reference prices ---------------------------------------

# Superset of the copilot backend's prices/latest query: same source_assets
# LEFT JOIN + is_single_rate (so the technical feed matches the copilot
# "platform compare" section byte-for-byte), PLUS s.role and the comma-separated
# `assets` filter. SEO reads a subset of these columns; technical reads the lot.
_LATEST_SQL = text(
    """
    SELECT s.slug      AS source_slug,
           s.title_en  AS source_title_en,
           s.title_fa  AS source_title_fa,
           s.role      AS source_role,
           a.slug      AS asset_slug,
           a.symbol    AS asset_symbol,
           a.std_symbol AS asset_std_symbol,
           a.title_en  AS asset_title_en,
           a.title_fa  AS asset_title_fa,
           a.type      AS asset_type,
           a.unit      AS asset_unit,
           c.code      AS currency_code,
           c.slug      AS currency_slug,
           c.symbol    AS currency_symbol,
           c.title_fa  AS currency_title_fa,
           c.title_en  AS currency_title_en,
           c.type      AS currency_type,
           sa.is_single_rate AS is_single_rate,
           pl.price,
           pl.bid,
           pl.ask,
           pl.crawled_at
    FROM   price_latest pl
    JOIN   sources    s ON s.id = pl.source_id
    JOIN   assets     a ON a.id = pl.asset_id
    JOIN   currencies c ON c.id = pl.currency_id
    LEFT JOIN source_assets sa
           ON sa.source_id = pl.source_id
          AND sa.asset_id  = pl.asset_id
          AND sa.deleted   = FALSE
    WHERE  s.deleted = FALSE
      AND  a.deleted = FALSE
      AND  c.deleted = FALSE
      AND  (CAST(:source   AS text) IS NULL OR s.slug = :source)
      AND  (CAST(:asset    AS text) IS NULL OR a.slug = :asset)
      AND  (CAST(:currency AS text) IS NULL OR c.slug = lower(:currency))
      AND  (CAST(:type     AS text) IS NULL OR a.type = :type)
      AND  (CAST(:assets   AS text) IS NULL
            OR a.slug = ANY(string_to_array(:assets, ',')))
    ORDER  BY s.slug, a.slug, c.slug
    """
)


async def latest_prices(
    session: AsyncSession,
    *,
    source: Optional[str] = None,
    asset: Optional[str] = None,
    currency: Optional[str] = None,
    type: Optional[str] = None,
    assets: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Latest quote per (source, asset, currency). All filters optional.

    `assets` is a comma-separated list of asset slugs (matches copilot's param).
    """
    result = await session.execute(
        _LATEST_SQL,
        {
            "source": source,
            "asset": asset,
            "currency": currency,
            "type": type,
            "assets": assets,
        },
    )
    return [dict(r) for r in result.mappings().all()]


# --- Latest supplier quotes --------------------------------------------------

_SUPPLIER_LATEST_SQL = text(
    """
    SELECT s.slug      AS source_slug,
           s.title_en  AS source_title_en,
           s.title_fa  AS source_title_fa,
           s.role      AS source_role,
           a.slug      AS asset_slug,
           a.symbol    AS asset_symbol,
           a.std_symbol AS asset_std_symbol,
           a.title_en  AS asset_title_en,
           a.title_fa  AS asset_title_fa,
           a.type      AS asset_type,
           a.unit      AS asset_unit,
           c.code      AS currency_code,
           c.slug      AS currency_slug,
           c.symbol    AS currency_symbol,
           c.title_fa  AS currency_title_fa,
           c.title_en  AS currency_title_en,
           c.type      AS currency_type,
           spl.buy_price,
           spl.sell_price,
           spl.crawled_at
    FROM   supplier_price_latest spl
    JOIN   sources    s ON s.id = spl.source_id
    JOIN   assets     a ON a.id = spl.asset_id
    JOIN   currencies c ON c.id = spl.currency_id
    WHERE  s.deleted = FALSE
      AND  a.deleted = FALSE
      AND  c.deleted = FALSE
      AND  (CAST(:source AS text) IS NULL OR s.slug = :source)
      AND  (CAST(:asset  AS text) IS NULL OR a.slug = :asset)
    ORDER  BY s.slug, a.slug
    """
)


# Per-source clean bid/ask over the fast price_latest mirror, for statistics.
# Replicates price_clean's normalization (canonical in the copilot DB) WITHOUT
# scanning price_history: strip the "-1" sentinel (pos_price = price only when
# > 0), then each side falls back to pos_price. So a single-rate source (price
# only) contributes its price to BOTH bid and ask; a dual-rate source contributes
# its real bid and ask; a "-1 + bid/ask" source contributes those. bid = خرید,
# ask = فروش. `age_seconds` uses the DB clock (NOW()) to avoid app/DB skew.
_STATS_ROWS_SQL = text(
    """
    SELECT s.slug      AS source_slug,
           s.title_fa  AS source_title_fa,
           s.title_en  AS source_title_en,
           s.role      AS source_role,
           a.slug      AS asset_slug,
           a.symbol    AS asset_symbol,
           a.std_symbol AS asset_std_symbol,
           a.title_en  AS asset_title_en,
           a.title_fa  AS asset_title_fa,
           a.type      AS asset_type,
           a.unit      AS asset_unit,
           c.code      AS currency_code,
           c.slug      AS currency_slug,
           c.symbol    AS currency_symbol,
           c.title_fa  AS currency_title_fa,
           c.title_en  AS currency_title_en,
           c.type      AS currency_type,
           pl.price,
           pl.bid,
           pl.ask,
           pl.crawled_at,
           EXTRACT(EPOCH FROM (NOW() - pl.crawled_at))::float8 AS age_seconds,
           COALESCE(pl.bid, CASE WHEN pl.price > 0 THEN pl.price END) AS bid_clean,
           COALESCE(pl.ask, CASE WHEN pl.price > 0 THEN pl.price END) AS ask_clean
    FROM   price_latest pl
    JOIN   sources    s ON s.id = pl.source_id
    JOIN   assets     a ON a.id = pl.asset_id
    JOIN   currencies c ON c.id = pl.currency_id
    WHERE  s.deleted = FALSE
      AND  a.deleted = FALSE
      AND  c.deleted = FALSE
      AND  (CAST(:asset    AS text) IS NULL OR a.slug = :asset)
      AND  (CAST(:currency AS text) IS NULL OR c.slug = lower(:currency))
      AND  (CAST(:role     AS text) IS NULL OR s.role = :role)
    ORDER  BY a.slug, c.slug, s.slug
    """
)


async def latest_clean_for_stats(
    session: AsyncSession,
    *,
    asset: Optional[str] = None,
    currency: Optional[str] = None,
    role: Optional[str] = None,
) -> list[dict[str, Any]]:
    """One row per source for each (asset, currency) with clean `bid_clean` /
    `ask_clean` + `age_seconds`.

    Both filters are optional: omit them to get every (asset, currency) pair
    that has a latest quote, ordered so rows of one pair arrive together
    (`asset`, then `currency`, then `source`) — the caller groups on that.

    Feeds the statistics endpoint. Either side may be None when a source has no
    usable quote for it — the caller skips those per side.
    """
    result = await session.execute(
        _STATS_ROWS_SQL, {"asset": asset, "currency": currency, "role": role}
    )
    return [dict(r) for r in result.mappings().all()]


async def latest_supplier_prices(
    session: AsyncSession,
    *,
    source: Optional[str] = None,
    asset: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Latest buy/sell quote per supplier (source, asset)."""
    result = await session.execute(
        _SUPPLIER_LATEST_SQL, {"source": source, "asset": asset}
    )
    return [dict(r) for r in result.mappings().all()]


# --- Reference catalogs ------------------------------------------------------

_ASSETS_SQL = text(
    """
    SELECT slug, symbol, std_symbol, title_en, title_fa, type, unit, purity
    FROM   assets
    WHERE  deleted = FALSE
      AND  (CAST(:type AS text) IS NULL OR type = :type)
    ORDER  BY type, slug
    """
)

_SOURCES_SQL = text(
    """
    SELECT slug, title_en, title_fa, type, role, url
    FROM   sources
    WHERE  deleted = FALSE
      AND  (CAST(:role AS text) IS NULL OR role = :role)
    ORDER  BY role, slug
    """
)


async def list_assets(
    session: AsyncSession, *, type: Optional[str] = None
) -> list[dict[str, Any]]:
    """The asset catalog (optionally filtered by type: gold/silver/coin/…)."""
    result = await session.execute(_ASSETS_SQL, {"type": type})
    return [dict(r) for r in result.mappings().all()]


async def list_sources(
    session: AsyncSession, *, role: Optional[str] = None
) -> list[dict[str, Any]]:
    """The source catalog (optionally filtered by role: platform/reference/…)."""
    result = await session.execute(_SOURCES_SQL, {"role": role})
    return [dict(r) for r in result.mappings().all()]
