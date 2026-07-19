"""Health / readiness endpoints — public (no API key), so a consumer (or a
monitor) can check the service before calling the data endpoints.

  GET /health        liveness  — is the process up? Cheap, touches nothing.
  GET /health/ready  readiness — can it actually serve data right now? Probes the
                     database (SELECT 1) and Redis (PING).

Readiness reflects the REAL serving contract:
  * The data endpoints need the DB. If the DB is down, the service is NOT ready
    → 503.
  * Rate limiting uses Redis but FAILS OPEN (see app.usage.ratelimit): if Redis
    is down, requests are still served (just unthrottled). So a Redis outage is
    reported as "degraded", not "not ready" — status stays 200.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.redis import get_redis
from app.db.session import SessionLocal
from app.shared.schemas import envelope, ok

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness — is the service process up?")
async def health():
    return ok({"status": "healthy"})


@router.get("/health/ready", summary="Readiness — can the service serve data now?")
async def ready():
    # DB — the hard dependency for every data endpoint.
    db_ok = False
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001 — a failed probe just means "down"
        db_ok = False

    # Redis — used for rate limiting, which fails open, so its downness is a
    # degradation, not an outage.
    redis_ok = False
    try:
        redis_ok = bool(await get_redis().ping())
    except Exception:  # noqa: BLE001
        redis_ok = False

    data = {
        "database": "ok" if db_ok else "down",
        "redis": "ok" if redis_ok else "down",
        "rate_limiting": "enforced" if redis_ok else "degraded (fail-open)",
    }

    # Ready as long as the DB is reachable — that's what "can I get data" means.
    if db_ok:
        message = "ready" if redis_ok else "ready (degraded: rate limiting off)"
        return ok(data, message=message)
    return envelope(False, "Service not ready: database unreachable", 503, data)
