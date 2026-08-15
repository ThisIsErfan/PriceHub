# Partner module: `reports`

The third section (beside `technical` and `seo`). A **reporting** feed for senior
management — not operational. Mounted at `/v1/reports`. Keys for this partner can
only call this namespace.

Intended consumer: an **Airflow DAG** that fetches this every ~2 minutes and posts
`data.message` to a private Telegram channel. PriceHub only serves the data +
message; it does not schedule or send anything.

## Endpoints

| Method | Path | Scope | Returns |
|--------|------|-------|---------|
| GET | `/v1/reports/platform-compare` | `reports:read` | Competitive report for one asset: leaderboard by **user-buy price** (platform sell/ask), market stats (excl. Gerami), Gerami's position, **+ a ready Persian Telegram message** |

Query: `asset` (required, e.g. `gold-18k`/`silver-999`/`copper`), `currency`
(a slug — the lowercase code, default `irt`), `max_age_seconds` (default 180 —
exclude sources stale >3min), `exclude` (comma-separated source slugs to drop).

The `asset` / `currency` in the response are the shared refs from
[`app/shared/refs.py`](../../shared/refs.py), identical to every other partner
endpoint — see [docs/api/responses.md](../../../docs/api/responses.md).

## Key ideas

- **User-buy price = the platform's sell/ask (فروش)** — what a customer pays to
  buy. The leaderboard sorts by it high→low; Gerami lower = more competitive.
- Statistics **exclude Gerami** (they describe the competition); Gerami is
  reported separately with its rank and distance from the market.
- Only **fresh** sources (updated within `max_age_seconds`) are ranked/counted;
  stale ones are listed under `market.excluded_stale`.
- `data.message` is a preformatted Persian message (Jalali date, Tehran time,
  Persian digits) the DAG can post as-is.

Data logic in [`service.py`](service.py); Persian/number/Jalali formatting +
message builder in [`format.py`](format.py).
