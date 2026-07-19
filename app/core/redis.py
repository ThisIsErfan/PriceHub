"""Shared async Redis client.

Backs rate limiting today (per-key per-second / per-minute windows) and is the
place a response cache would live later. One connection pool for the process,
created lazily on first use and reused thereafter.
"""

from __future__ import annotations

import redis.asyncio as redis

from app.core.config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return the process-wide async Redis client (created on first call)."""
    global _client
    if _client is None:
        _client = redis.Redis(
            host=settings.PRICEHUB_REDIS_HOST,
            port=settings.PRICEHUB_REDIS_PORT,
            password=settings.PRICEHUB_REDIS_PASSWORD or None,
            db=settings.PRICEHUB_REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


async def close_redis() -> None:
    """Close the client on application shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
