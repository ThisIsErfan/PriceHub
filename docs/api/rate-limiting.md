# Rate limiting

PriceHub caps how fast each API key can call, to protect the shared crawler
database. Limits are enforced in Redis (see
[../architecture/redis.md](../architecture/redis.md)).

## The limits

Two windows apply **per API key**, both must pass:

| Window | Default cap | Purpose |
|--------|-------------|---------|
| Per second | **5 requests/second** | absorbs short bursts, blocks floods |
| Per minute | **120 requests/minute** | ~2 req/s sustained — comfortably above real use |

These defaults are deliberately conservative. They are set in config
(`DEFAULT_RATE_LIMIT_PER_SEC`, `DEFAULT_RATE_LIMIT_PER_MIN`) and can be **overridden
per key** in the database (`partner_api_keys.rate_limit_per_sec` /
`rate_limit_per_min`) when a specific partner needs more or less.

### Why these numbers

The data updates on the order of seconds (supplier ticks ~5s; most sources
slower). A consumer polling once every few seconds is far under 120/min, so the
caps never bite real usage — they only stop runaway loops and scrapers. A single
key at the cap is ~2 req/s of tiny indexed reads, which the mirror tables
(`price_latest`, `supplier_price_latest`) serve in constant time.

## What a limited response looks like

When a window is exceeded, the API returns **HTTP 429** with the standard envelope
and a `Retry-After` header:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 37
```
```json
{
  "success": false,
  "message": "Rate limit exceeded. Slow down and retry.",
  "responseCode": 429,
  "data": null
}
```

- Exceeding the **per-second** cap → `Retry-After: 1`.
- Exceeding the **per-minute** cap → `Retry-After: <seconds until the minute rolls over>`.

## Client guidance

- Poll no faster than you need; cache on your side where you can.
- On `429`, wait for `Retry-After` seconds, then retry (exponential backoff for
  repeated 429s is good manners).
- Need a higher limit? Ask for a per-key override rather than working around it.

## Degraded mode

If Redis is temporarily unreachable, the limiter **fails open** by default
(requests are allowed, auth still enforced) so availability is preserved. This is
configurable (`RATE_LIMIT_FAIL_OPEN`).
