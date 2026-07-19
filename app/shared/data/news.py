"""Reusable read queries over the news schema (``news_schm``).

Serves the crawled metals/crypto news. Full article bodies (``body_markdown``)
are intentionally NOT exposed here — partner endpoints return headline-level
metadata (title, summary, publisher, link, published_at); a module can opt into
the body explicitly if a partner is authorised for it.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_LATEST_NEWS_SQL = text(
    """
    SELECT n.title,
           n.summary,
           n.url,
           n.publisher,
           n.author,
           n.image_url,
           n.lang,
           n.published_at,
           n.crawled_at,
           src.slug     AS source_slug,
           src.title_en AS source_title_en
    FROM   news_schm.news_articles n
    JOIN   news_schm.news_sources  src ON src.id = n.source_id
    WHERE  src.deleted = FALSE
      AND  (CAST(:symbol AS text) IS NULL OR EXISTS (
                SELECT 1
                FROM   news_schm.news_article_symbols nas
                JOIN   news_schm.news_symbols sym ON sym.id = nas.symbol_id
                WHERE  nas.article_id = n.id
                  AND  sym.slug = :symbol))
    ORDER  BY n.published_at DESC NULLS LAST, n.crawled_at DESC
    LIMIT  :limit
    """
)


async def latest_news(
    session: AsyncSession,
    *,
    symbol: Optional[str] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Most recent articles (optionally by metal symbol: gold/silver/copper).

    ``limit`` is clamped to a sane ceiling by the caller/route.
    """
    result = await session.execute(
        _LATEST_NEWS_SQL, {"symbol": symbol, "limit": limit}
    )
    return [dict(r) for r in result.mappings().all()]
