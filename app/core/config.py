"""Application settings, loaded from environment / .env.

All PriceHub-specific env vars are prefixed to stay clearly separate from the
pricing-copilot backend's own vars (they never share a process, but the prefix
keeps GitHub Actions secrets/vars unambiguous):

    PARTNER_DB_*        the SELECT-only DB role PriceHub connects as
    PRICEHUB_REDIS_*    the Redis instance backing rate limits
    PRICEHUB_*          everything else app-level
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Database (reuses the crawler Postgres; SELECT-only role) -------------
    # Same cluster/database as the crawlers + copilot backend, reached by service
    # name on the shared pricing-net network. PriceHub connects as partner_api_usr:
    # SELECT on price/news data, and only INSERT/UPDATE on partner_schm usage.
    DB_HOST: str = "postgres-crawlers"
    DB_PORT: int = 5432
    DB_NAME: str = "pricing_db"
    PARTNER_DB_USER: str = "partner_api_usr"
    PARTNER_DB_PASSWORD: str = ""

    # --- Redis (rate-limit windows + ephemeral counters) ---------------------
    PRICEHUB_REDIS_HOST: str = "pricehub-redis"
    PRICEHUB_REDIS_PORT: int = 6379
    PRICEHUB_REDIS_PASSWORD: str = ""
    PRICEHUB_REDIS_DB: int = 0

    # --- App -----------------------------------------------------------------
    APP_ENV: str = "development"
    # Partner APIs are server-to-server, so CORS is normally irrelevant. Kept
    # configurable (comma-separated) in case a browser client is ever authorised.
    PARTNER_CORS_ORIGINS: str = ""

    # --- Rate limiting (defaults; each key may override in the DB) ------------
    # Two windows guard the server: a per-second burst cap and a per-minute
    # sustained cap. Chosen conservatively so a busy or misbehaving partner can
    # never overwhelm the shared crawler DB (see docs/api/rate-limiting.md).
    #   5 req/s   → short bursts are fine, floods are not.
    #   120 req/min → 2 req/s sustained average, comfortably above real use.
    DEFAULT_RATE_LIMIT_PER_SEC: int = 5
    DEFAULT_RATE_LIMIT_PER_MIN: int = 120

    # If Redis is unreachable, fail-open (allow the request, skip the limit) so a
    # Redis blip never takes the whole API down. Rate limiting is a guard rail,
    # not the auth boundary — auth still runs. Set False to fail-closed instead.
    RATE_LIMIT_FAIL_OPEN: bool = True

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.PARTNER_CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
