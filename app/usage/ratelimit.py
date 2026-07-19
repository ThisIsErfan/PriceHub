"""Redis-backed rate limiting — the server's guard rail against floods.

Two fixed windows are enforced per API key, both cheap atomic counters in Redis:

    ratelimit:{key_id}:s:{unix_second}   capped at rate_limit_per_sec   (burst)
    ratelimit:{key_id}:m:{unix_minute}   capped at rate_limit_per_min   (sustained)

Each request INCRements the current second's and minute's counters and rejects
(HTTP 429) if either exceeds its cap. Counters carry a short TTL, so they expire
on their own — no cleanup, no unbounded growth. This is a *fixed-window*
limiter: simple, O(1), and more than adequate to protect the shared crawler DB.
It is a guard rail, not the auth boundary — see RATE_LIMIT_FAIL_OPEN.

Why Redis and not Postgres: these counters are read+written on EVERY request and
are purely ephemeral. Putting them on the crawler DB's disk would add load to the
very database we are trying to protect. Durable "how many calls" counting lives
separately in Postgres (see app.usage.recorder).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from redis.exceptions import RedisError

from app.core.config import settings
from app.core.redis import get_redis


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    scope: str          # "second" | "minute" | "" when allowed
    limit: int          # the cap that applied
    retry_after: int    # seconds the caller should wait before retrying


async def check_rate_limit(
    key_id: int, per_sec: int, per_min: int
) -> RateDecision:
    """Increment this key's per-second and per-minute windows; decide allow/deny.

    On any Redis failure we honour RATE_LIMIT_FAIL_OPEN (default: allow) so a
    Redis blip degrades gracefully rather than taking the API down.
    """
    now = int(time.time())
    sec_bucket = now
    min_bucket = now // 60

    sec_key = f"ratelimit:{key_id}:s:{sec_bucket}"
    min_key = f"ratelimit:{key_id}:m:{min_bucket}"

    try:
        redis = get_redis()
        pipe = redis.pipeline()
        pipe.incr(sec_key)
        pipe.expire(sec_key, 2)      # a hair over one second
        pipe.incr(min_key)
        pipe.expire(min_key, 120)    # a hair over one minute
        sec_count, _, min_count, _ = await pipe.execute()
    except RedisError:
        if settings.RATE_LIMIT_FAIL_OPEN:
            return RateDecision(True, "", 0, 0)
        return RateDecision(False, "unavailable", 0, 1)

    if sec_count > per_sec:
        return RateDecision(False, "second", per_sec, 1)
    if min_count > per_min:
        # Tell the caller how long until this minute-window rolls over.
        return RateDecision(False, "minute", per_min, 60 - (now % 60))
    return RateDecision(True, "", 0, 0)
