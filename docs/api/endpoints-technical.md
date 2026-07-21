# Technical partner endpoints

Base: `https://api.gerami.online/v1/technical`
Auth: `X-API-Key` for a key on partner `technical`.
All GET. See [responses.md](responses.md) for the envelope and full examples.

Served by the code module [`app/partners/technical/`](../../app/partners/technical/).
This feed returns fuller rows than `seo` (every source, bid/ask, supplier quotes)
for machine integration.

Every asset in the response carries `std_symbol` — the standard/ISO metal code
(`XAU` gold, `XAG` silver, `XCU` copper), `null` for assets without one. Inputs
are unchanged: you still pass the **slug** (e.g. `gold-18k`) as `asset`.

## Endpoints

- [GET /v1/technical/prices/platforms/latest](#get-v1technicalpricesplatformslatest) — latest quote for **every** platform/asset/currency, with `bid`/`ask`
- [GET /v1/technical/prices/suppliers/latest](#get-v1technicalpricessupplierslatest) — latest supplier buy/sell quotes
- [GET /v1/technical/prices/stats](#get-v1technicalpricesstats) — cross-source statistical summary (`bid`/`ask`, separately) for one asset

---

## GET /v1/technical/prices/platforms/latest

Latest quote for **every** (platform, asset, currency), as `bid`/`ask` — nested
`source`/`asset`/`currency` refs plus `is_single_rate`.

There is **no bare `price` field**: a **single-rate** source quotes one number for
both sides, so it is surfaced as `bid == ask` (and `is_single_rate: true`). This
keeps the technical feed uniform — you always read `bid`/`ask` and never special-
case a `price`-only row.

To pull **one asset across all platforms**, just pass `asset` (e.g.
`?asset=gold-18k&currency=IRT`).

**Scope:** `prices:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | string | – | filter by platform (source) slug (e.g. `tgju`, `gerami`) |
| `asset` | string | – | asset slug — e.g. `gold-18k` (طلا), `silver-999` (نقره), `copper` (مس) |
| `currency` | string | – | filter by currency code (e.g. `IRT`, `IRR`, `USD`) |
| `type` | string | – | filter by asset type (e.g. `gold`, `currency`, `crypto`) |
| `assets` | string | – | comma-separated list of asset slugs |

```bash
curl -H "X-API-Key: $KEY" \
  "https://api.gerami.online/v1/technical/prices/platforms/latest?asset=gold-18k&currency=IRT"
```

`data`:
```json
{
  "items": [
    {
      "source":   { "slug": "gerami", "title_en": "Gerami", "title_fa": "گرمی" },
      "asset":    { "slug": "gold-18k", "symbol": "GOLD_18K", "std_symbol": "XAU", "title_fa": "طلای ۱۸ عیار", "unit": "per_gram" },
      "currency": { "code": "IRT", "title_fa": "تومان" },
      "is_single_rate": false,
      "bid": "3820000.00000000",
      "ask": "3830000.00000000",
      "crawled_at": "2026-07-19T08:41:12+00:00"
    },
    {
      "source":   { "slug": "tgju", "title_en": "TGJU", "title_fa": "طلا و جواهر" },
      "asset":    { "slug": "gold-18k", "symbol": "GOLD_18K", "std_symbol": "XAU", "title_fa": "طلای ۱۸ عیار", "unit": "per_gram" },
      "currency": { "code": "IRT", "title_fa": "تومان" },
      "is_single_rate": true,
      "bid": "18453900.00000000",
      "ask": "18453900.00000000",
      "crawled_at": "2026-07-19T08:41:10+00:00"
    }
  ],
  "count": 2,
  "generated_at": "2026-07-19T08:41:20.123456+00:00"
}
```

> Differences from the copilot `prices/latest`: the bare `price` field is dropped
> (single-rate rows report `bid == ask` instead), and each asset carries
> `std_symbol` (standard metal code `XAU`/`XAG`/`XCU`, `null` when absent). The
> `source`/`asset`/`currency` refs and `is_single_rate` are otherwise the same.

---

## GET /v1/technical/prices/suppliers/latest

Latest supplier **buy/sell** quotes.

**Scope:** `prices:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | string | – | filter by supplier slug (e.g. `zariran`, `abshodeasil`) |
| `asset` | string | – | asset slug — e.g. `gold-18k` (طلا), `silver-999` (نقره), `copper` (مس) |

```bash
curl -H "X-API-Key: $KEY" "https://api.gerami.online/v1/technical/prices/suppliers/latest"
```

`data`: `{ items: [ {supplier, supplier_title_fa, asset, std_symbol, unit, currency, buy_price, sell_price, crawled_at} ], count }`

(`asset` is the slug; `std_symbol` is the standard metal code, `null` when absent.)

---

## GET /v1/technical/prices/stats

Cross-source **statistical summary** for one (asset, currency), computed from the
latest platform quotes. Statistics are computed **separately for `bid` (خرید) and
`ask` (فروش)**, each over that side's clean per-source value (the `-1` sentinel is
stripped; a **single-rate** source's `price` counts on **both** sides). Sources
whose newest sample is **older than `max_age_seconds` (default 180s)** are
excluded — we crawl every ~120s, so a source silent for >3min is treated as stale
and left out.

**Gerami is deliberately excluded from the statistics** and returned separately
under `gerami` (its own current quote + how far it sits from the market
mean/median), so the stats represent the rest of the market and you compare your
own price against them.

**Scope:** `prices:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `asset` | string | **required** | asset slug — e.g. `gold-18k` (طلا), `silver-999` (نقره), `copper` (مس) |
| `currency` | string | **required** | currency code, e.g. `IRT` |
| `max_age_seconds` | int (30–3600) | `180` | exclude sources not updated within this window |
| `role` | string | – | restrict the sample to a source role: `platform` or `reference` |

```bash
curl -H "X-API-Key: $KEY" \
  "https://api.gerami.online/v1/technical/prices/stats?asset=gold-18k&currency=IRT"
```

Statistics are computed **separately for `bid` (خرید) and `ask` (فروش)**, each
over its own per-source values.

`data`:
```json
{
  "asset":    { "slug": "gold-18k", "symbol": "GOLD_18K", "std_symbol": "XAU", "title_fa": "طلای ۱۸ عیار", "unit": "per_gram" },
  "currency": { "code": "IRT", "title_fa": "تومان" },
  "as_of": "2026-07-19T15:32:25+00:00",
  "params": { "max_age_seconds": 180, "role": null },
  "sample": {
    "total_sources": 17,
    "included": 16,
    "excluded": 1,
    "included_sources": ["daric", "digikala", "..."],
    "excluded_sources": [ { "slug": "invi", "age_seconds": 250, "reason": "stale" } ]
  },
  "stats": {
    "bid": {
      "sample_count": 16,
      "min": "18701243.00", "max": "18839300.00",
      "mean": "18765720.00", "median": "18760000.00", "stdev": "41250.10",
      "mean_2sigma": "18763900.00", "count_2sigma": 15,
      "mean_3sigma": "18765720.00", "count_3sigma": 16
    },
    "ask": {
      "sample_count": 16,
      "min": "18738000.00", "max": "18930180.00",
      "mean": "18801984.00", "median": "18800000.00", "stdev": "45452.07",
      "mean_2sigma": "18799000.00", "count_2sigma": 15,
      "mean_3sigma": "18801984.00", "count_3sigma": 16
    }
  },
  "gerami": {
    "price": "18777477.00",
    "bid": "18701243.00",
    "ask": "18777477.00",
    "crawled_at": "2026-07-19T15:32:02+00:00",
    "age_seconds": 41,
    "bid_vs_market": { "diff_from_median": "-58757.00", "diff_from_mean": "-64477.00" },
    "ask_vs_market": { "diff_from_median": "-22523.00", "diff_from_mean": "-24507.00" }
  }
}
```

Field notes:
- **`stats.bid` / `stats.ask`** are computed independently, each over that side's
  clean value per source. A **single-rate** source (only a `price`, no buy/sell
  split) contributes that price to **both** sides; a dual-rate source contributes
  its real bid and ask; the `-1` sentinel is stripped first. Each block has its
  own `sample_count` (a source missing one side just doesn't count on that side).
- **`mean_2sigma` / `mean_3sigma`** are single-pass sigma-clipped means: drop
  values more than k·σ from that side's mean, then re-average. `count_Nsigma` is
  how many remained. With very few sources a lone outlier can inflate σ enough to
  survive (statistical masking) — expected behaviour.
- **`stats.bid` / `stats.ask`** are `null` when no fresh source has a usable value
  for that side. All monetary values are strings (2 dp), like the rest of the feed.
- **`excluded_sources[].reason`** is `stale` (too old) or `no_price` (no usable
  quote on either side).
- **Gerami is excluded from the statistics** and returned under `gerami` (its own
  quote + `bid_vs_market` / `ask_vs_market`, each comparing Gerami's side to the
  market's stats for that side).

> Prefer `stats` when you want the market summary; `platforms/latest` when you
> want each platform's row (optionally scoped to one `asset`).
