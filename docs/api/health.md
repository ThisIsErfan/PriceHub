# Health & readiness

Two **public** endpoints (no API key) so a consumer — or a monitor — can check
the service before calling the data endpoints. Both appear in the OpenAPI docs
(`/docs`).

There is deliberately **no per-endpoint health check**: every data endpoint
shares the same backing database, so one readiness probe answers "will the data
endpoints work right now?" for all of them.

## GET /health — liveness

"Is the service process up?" Cheap; touches no dependencies. Use it for uptime
pings / load-balancer liveness.

```bash
curl -s https://api.gerami.online/health
```
```json
{ "success": true, "message": "OK", "responseCode": 200, "data": { "status": "healthy" } }
```

Always `200` while the process is running.

## GET /health/ready — readiness

"Can the service actually serve data right now?" Probes the database (`SELECT 1`)
and Redis (`PING`). **Call this before your first request** if you want to fail
fast on an outage.

```bash
curl -s https://api.gerami.online/health/ready
```

**Ready (all good) → `200`:**
```json
{
  "success": true,
  "message": "ready",
  "responseCode": 200,
  "data": { "database": "ok", "redis": "ok", "rate_limiting": "enforced" }
}
```

**Ready but degraded → `200`** (DB up, Redis down — data still serves; rate
limiting is temporarily off because it fails open):
```json
{
  "success": true,
  "message": "ready (degraded: rate limiting off)",
  "responseCode": 200,
  "data": { "database": "ok", "redis": "down", "rate_limiting": "degraded (fail-open)" }
}
```

**Not ready → `503`** (database unreachable — data endpoints will fail):
```json
{
  "success": false,
  "message": "Service not ready: database unreachable",
  "responseCode": 503,
  "data": { "database": "down", "redis": "down", "rate_limiting": "degraded (fail-open)" }
}
```

### How to read it

| `responseCode` | Meaning | Should you call data endpoints? |
|----------------|---------|--------------------------------|
| `200` `ready` | fully healthy | yes |
| `200` `ready (degraded…)` | DB ok, Redis down; unthrottled | yes (rate limits not enforced meanwhile) |
| `503` | DB unreachable | no — retry later |

### Notes

- Both endpoints are **unauthenticated** on purpose, so you can probe them even
  before you have a key.
- Readiness treats the **database** as the hard dependency; **Redis** only powers
  rate limiting, which fails open, so its downness is a degradation — not an
  outage (see [rate-limiting.md](rate-limiting.md)).
