# Partner module: `technical`

Serves the **technical team** integrating raw data. Mounted at `/v1/technical`.
Keys for this partner can only call these routes (an `seo` key gets `403` here).

## Endpoints

| Method | Path | Scope | Returns |
|--------|------|-------|---------|
| GET | `/v1/technical/prices/latest` | `prices:read` | Latest quote per source/asset/currency, **with bid/ask** (`?source=`, `?asset=`, `?currency=`, `?type=`) |
| GET | `/v1/technical/suppliers/latest` | `prices:read` | Latest supplier buy/sell/mid quotes (`?source=`, `?asset=`) |
| GET | `/v1/technical/sources` | `reference:read` | Source catalog (`?role=platform\|reference\|supplier`) |
| GET | `/v1/technical/assets` | `reference:read` | Asset catalog (`?type=`) |

This feed intentionally returns fuller rows than `seo` (every source, bid/ask,
supplier quotes) for machine integration.

## Add / change technical endpoints

Edit [`service.py`](service.py) and [`router.py`](router.py). Keep every route
GET and behind `require_partner("technical", scope=…)`.
