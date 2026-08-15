# Partner module: `technical`

Serves the **technical team** integrating raw data. Mounted at `/v1/technical`.
Keys for this partner can only call these routes (an `seo` key gets `403` here).

## Endpoints

| Method | Path | Scope | Returns |
|--------|------|-------|---------|
| GET | `/v1/technical/prices/platforms/latest` | `prices:read` | Latest quote per platform/asset/currency as **bid/ask** (no bare `price`; single-rate → `bid == ask`) (`?source=`, `?asset=`, `?currency=`, `?type=`, `?assets=`); pass `?asset=` for one asset across all platforms |
| GET | `/v1/technical/prices/suppliers/latest` | `prices:read` | Latest supplier buy/sell quotes (`?source=`, `?asset=`) |
| GET | `/v1/technical/prices/stats` | `prices:read` | Cross-source **statistical summary** for one asset (mean/median/2σ/3σ trimmed/min/max), stale sources excluded, + Gerami's quote |

`platforms/latest` follows the copilot `GET /api/v1/prices/latest`
(platform-compare) shape — nested source/asset/currency refs + `is_single_rate` —
but exposes quotes as `bid`/`ask` only (no bare `price`; single-rate → `bid ==
ask`). `stats` summarizes each source's clean `bid` and `ask` **separately**
(the `-1` sentinel stripped; a single-rate source counts on both sides), with
stale sources and Gerami excluded from the sample.

Every asset in the response carries `asset.symbol` — the standard instrument
code, purity + unit qualified (`XAU750g`/`XAG999g`/`XCU9999g`); assets with no
standard code agreed yet fall back to the internal code (`GOLD_24K`). Inputs
stay the slug (e.g. `gold-18k`). `currency` carries both its `code` (`IRT`) and
its display `symbol` (`T`).

## Add / change technical endpoints

Edit [`service.py`](service.py) and [`router.py`](router.py). Keep every route
GET and behind `require_partner("technical", scope=…)`.
