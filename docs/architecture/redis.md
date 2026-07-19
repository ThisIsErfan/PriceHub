# Redis in PriceHub — exactly what it does

Short version: **Redis is the request-rate guard rail.** It keeps fast, ephemeral
counters that enforce per-key rate limits so a busy or misbehaving consumer can
never overload the shared crawler database. Durable "how many calls did partner X
make" counting is **not** Redis's job — that lives in Postgres.

## The one job it does today: rate limiting

For every request, PriceHub increments two atomic counters in Redis and rejects
the request (`429`) if either exceeds its cap:

| Redis key | Meaning | Cap (default) | TTL |
|-----------|---------|---------------|-----|
| `ratelimit:{key_id}:s:{unix_second}` | requests this second | `5/sec` (burst) | ~2s |
| `ratelimit:{key_id}:m:{unix_minute}` | requests this minute | `120/min` (sustained) | ~120s |

Because each counter carries a short TTL, it expires by itself — there is no
cleanup job and no unbounded growth. This is a **fixed-window** limiter: O(1),
trivially cheap, and more than enough to protect the DB. See
[../api/rate-limiting.md](../api/rate-limiting.md) for the consumer-facing rules.

### Why Redis and not Postgres for this

These counters are read **and** written on **every** request and are purely
throwaway. Putting them on the crawler DB's disk would pile load onto the exact
database we are trying to shield. Redis holds them in memory, atomically, off the
DB's back.

### If Redis is down

Rate limiting is a guard rail, not the auth boundary. By default
(`RATE_LIMIT_FAIL_OPEN=true`) a Redis outage makes the limiter **fail open** — the
request is allowed and auth still runs — so a Redis blip never takes the whole API
down. Set it to `false` to fail closed instead.

## What Redis explicitly does NOT do

- **It does not store the durable usage history.** Every request is also rolled up
  into `partner_schm.partner_usage_daily` in Postgres (one row per key/day/
  endpoint). That table is the source of truth for reporting and billing-style
  questions — it survives restarts and Redis flushes. Redis counters are
  short-lived and would be the wrong place for history.
- **It is not the auth store.** Keys live (hashed) in Postgres.

## Reserved for later (already provisioned)

Redis is the natural home for a **response cache** (e.g. cache `prices/latest` for
a few seconds so repeated partner polls don't each hit the DB). Nothing uses it
for caching yet, but the client and container are in place, so adding it later is
a code-only change.

## Operational footprint

`pricehub-redis` runs `redis:7-alpine` with `--maxmemory 128mb`,
`--maxmemory-policy allkeys-lru`, persistence disabled (`--save ""`), a password,
and **no host port** (reachable only by `pricehub` over `pricing-net`). Its memory
use is tiny and self-capping.
