# Partner module: `technical`

Serves the **technical team** integrating raw data. Mounted at `/v1/technical`.
Keys for this partner can only call these routes (an `seo` key gets `403` here).

## Endpoints

| Method | Path | Scope | Returns |
|--------|------|-------|---------|
| GET | `/v1/technical/prices/latest` | `prices:read` | Latest quote per source/asset/currency, **with bid/ask** (`?source=`, `?asset=`, `?currency=`, `?type=`, `?assets=`) |
| GET | `/v1/technical/prices/compare` | `prices:read` | One asset's latest price across **all** sources (`asset` required, `?currency=`) — same shape as `latest` |
| GET | `/v1/technical/prices/stats` | `prices:read` | Cross-source **statistical summary** for one asset (mean/median/2σ/3σ trimmed/min/max), stale sources excluded, + Gerami's quote |
| GET | `/v1/technical/suppliers/latest` | `prices:read` | Latest supplier buy/sell/mid quotes (`?source=`, `?asset=`) |

`latest`/`compare` mirror the copilot `GET /api/v1/prices/latest`
(platform-compare) — nested source/asset/currency refs + `is_single_rate` +
bid/ask. `stats` computes over each source's clean `mid` (matching the copilot
consensus definition).

## Add / change technical endpoints

Edit [`service.py`](service.py) and [`router.py`](router.py). Keep every route
GET and behind `require_partner("technical", scope=…)`.
