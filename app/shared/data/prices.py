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

_LATEST_SQL = text(
    """
    SELECT s.slug      AS source_slug,
           s.title_en  AS source_title_en,
           s.title_fa  AS source_title_fa,
           s.role      AS source_role,
           a.slug      AS asset_slug,
           a.symbol    AS asset_symbol,
           a.title_en  AS asset_title_en,
           a.title_fa  AS asset_title_fa,
           a.type      AS asset_type,
           a.unit      AS asset_unit,
           c.code      AS currency_code,
           c.title_fa  AS currency_title_fa,
           pl.price,
           pl.bid,
           pl.ask,
           pl.crawled_at
    FROM   price_latest pl
    JOIN   sources    s ON s.id = pl.source_id
    JOIN   assets     a ON a.id = pl.asset_id
    JOIN   currencies c ON c.id = pl.currency_id
    WHERE  s.deleted = FALSE
      AND  a.deleted = FALSE
      AND  c.deleted = FALSE
      AND  (CAST(:source   AS text) IS NULL OR s.slug = :source)
      AND  (CAST(:asset    AS text) IS NULL OR a.slug = :asset)
      AND  (CAST(:currency AS text) IS NULL OR c.code = :currency)
      AND  (CAST(:type     AS text) IS NULL OR a.type = :type)
    ORDER  BY s.slug, a.slug, c.code
    """
)


async def latest_prices(
    session: AsyncSession,
    *,
    source: Optional[str] = None,
    asset: Optional[str] = None,
    currency: Optional[str] = None,
    type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Latest quote per (source, asset, currency). All filters optional."""
    result = await session.execute(
        _LATEST_SQL,
        {"source": source, "asset": asset, "currency": currency, "type": type},
    )
    return [dict(r) for r in result.mappings().all()]


# --- Latest supplier quotes --------------------------------------------------

_SUPPLIER_LATEST_SQL = text(
    """
    SELECT s.slug      AS source_slug,
           s.title_en  AS source_title_en,
           s.title_fa  AS source_title_fa,
           a.slug      AS asset_slug,
           a.symbol    AS asset_symbol,
           a.title_fa  AS asset_title_fa,
           a.unit      AS asset_unit,
           c.code      AS currency_code,
           spl.buy_price,
           spl.sell_price,
           spl.mid_price,
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
    SELECT slug, symbol, title_en, title_fa, type, unit, purity
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
