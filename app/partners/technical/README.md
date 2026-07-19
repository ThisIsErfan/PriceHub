# Partner module: `technical`

Serves the **technical team** integrating raw data. Mounted at `/v1/technical`.
Keys for this partner can only call these routes (an `seo` key gets `403` here).

## Endpoints

| Method | Path | Scope | Returns |
|--------|------|-------|---------|
| GET | `/v1/technical/prices/latest` | `prices:read` | Latest quote per source/asset/currency, **with bid/ask** (`?source=`, `?asset=`, `?currency=`, `?type=`, `?assets=`) |
| GET | `/v1/technical/suppliers/latest` | `prices:read` | Latest supplier buy/sell/mid quotes (`?source=`, `?asset=`) |

Only these two endpoints are exposed for now. The response shape mirrors the
copilot `GET /api/v1/prices/latest` (platform-compare) — nested
source/asset/currency refs + `is_single_rate` + bid/ask.

## Add / change technical endpoints

Edit [`service.py`](service.py) and [`router.py`](router.py). Keep every route
GET and behind `require_partner("technical", scope=…)`.
