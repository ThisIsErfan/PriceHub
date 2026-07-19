# Technical partner endpoints

Base: `https://api.gerami.online/v1/technical`
Auth: `X-API-Key` for a key on partner `technical`.
All GET. See [responses.md](responses.md) for the envelope and full examples.

Served by the code module [`app/partners/technical/`](../../app/partners/technical/).
This feed returns fuller rows than `seo` (every source, bid/ask, supplier quotes)
for machine integration.

---

## GET /v1/technical/prices/latest

Latest quote for **every** (source, asset, currency), including `bid`/`ask`. This
is the **same payload shape** as the copilot backend's
`GET /api/v1/prices/latest` (the "platform compare" section) — nested
`source`/`asset`/`currency` refs plus `is_single_rate` — so an existing copilot
consumer can point at this endpoint unchanged.

**Scope:** `prices:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | string | – | filter by source (platform) slug (e.g. `tgju`, `gerami`) |
| `asset` | string | – | filter by asset slug (e.g. `gold-18k`, `gold-ounce`) |
| `currency` | string | – | filter by currency code (e.g. `IRT`, `IRR`, `USD`) |
| `type` | string | – | filter by asset type (e.g. `gold`, `currency`, `crypto`) |
| `assets` | string | – | comma-separated list of asset slugs |

```bash
curl -H "X-API-Key: $KEY" \
  "https://api.gerami.online/v1/technical/prices/latest?asset=gold-18k&currency=IRT"
```

`data`:
```json
{
  "items": [
    {
      "source":   { "slug": "gerami", "title_en": "Gerami", "title_fa": "گرمی" },
      "asset":    { "slug": "gold-18k", "symbol": "GOLD_18K", "title_fa": "طلای ۱۸ عیار", "unit": "per_gram" },
      "currency": { "code": "IRT", "title_fa": "تومان" },
      "is_single_rate": false,
      "price": "3825000.00000000",
      "bid": "3820000.00000000",
      "ask": "3830000.00000000",
      "crawled_at": "2026-07-19T08:41:12+00:00"
    }
  ],
  "count": 1,
  "generated_at": "2026-07-19T08:41:20.123456+00:00"
}
```

> Mirrors copilot exactly except the outer envelope: copilot nests this under its
> own `{success,message,responseCode,data}`, and so does PriceHub — the `data`
> block is identical.

---

## GET /v1/technical/suppliers/latest

Latest supplier **buy/sell/mid** quotes.

**Scope:** `prices:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | string | – | filter by supplier slug (e.g. `zariran`, `abshodeasil`) |
| `asset` | string | – | filter by asset slug |

```bash
curl -H "X-API-Key: $KEY" "https://api.gerami.online/v1/technical/suppliers/latest"
```

`data`: `{ items: [ {supplier, supplier_title_fa, asset, unit, currency, buy_price, sell_price, mid_price, crawled_at} ], count }`

---

---

## GET /v1/technical/prices/compare

One asset's latest price across **all** sources — "compare this asset everywhere".
Same `data` shape as `prices/latest`; `asset` is **required** so the intent is
explicit.

**Scope:** `prices:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `asset` | string | **required** | asset slug, e.g. `gold-18k` |
| `currency` | string | – | currency code, e.g. `IRT`, `IRR` |

```bash
curl -H "X-API-Key: $KEY" \
  "https://api.gerami.online/v1/technical/prices/compare?asset=gold-18k&currency=IRT"
```

`data`: identical to `prices/latest` (nested source/asset/currency + `is_single_rate` + price/bid/ask).

---

## GET /v1/technical/prices/stats

Cross-source **statistical summary** for one (asset, currency), computed from the
latest platform quotes. Each source contributes its **clean `mid`** (the `-1`
sentinel is stripped and `mid = (bid+ask)/2`, matching the copilot consensus
definition). Sources whose newest sample is **older than `max_age_seconds`
(default 180s)** are excluded — we crawl every ~120s, so a source silent for
>3min is treated as stale and left out. Gerami's own current quote is always
surfaced separately for reference.

**Scope:** `prices:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `asset` | string | **required** | asset slug, e.g. `gold-18k` |
| `currency` | string | **required** | currency code, e.g. `IRT` |
| `max_age_seconds` | int (30–3600) | `180` | exclude sources not updated within this window |
| `role` | string | – | restrict the sample to a source role: `platform` or `reference` |

```bash
curl -H "X-API-Key: $KEY" \
  "https://api.gerami.online/v1/technical/prices/stats?asset=gold-18k&currency=IRT"
```

`data`:
```json
{
  "asset":    { "slug": "gold-18k", "symbol": "GOLD_18K", "title_fa": "طلای ۱۸ عیار", "unit": "per_gram" },
  "currency": { "code": "IRT", "title_fa": "تومان" },
  "as_of": "2026-07-19T15:32:25+00:00",
  "params": { "max_age_seconds": 180, "role": null },
  "sample": {
    "total_sources": 18,
    "included": 17,
    "excluded": 1,
    "included_sources": ["daric", "digikala", "gerami", "..."],
    "excluded_sources": [ { "slug": "invi", "age_seconds": 250, "reason": "stale" } ]
  },
  "stats": {
    "min": "18738000.00",
    "max": "18847000.00",
    "mean": "18781234.50",
    "median": "18777477.00",
    "stdev": "41250.10",
    "mean_2sigma": "18779900.00",   // mean after dropping points beyond ±2σ
    "count_2sigma": 17,
    "mean_3sigma": "18781234.50",   // mean after dropping points beyond ±3σ
    "count_3sigma": 18
  },
  "gerami": {
    "price": "18777477.00",
    "bid": "18701243.00",
    "ask": "18777477.00",
    "mid": "18739360.00",
    "crawled_at": "2026-07-19T15:32:02+00:00",
    "age_seconds": 41,
    "included_in_stats": true,
    "diff_from_median": "-38117.00",
    "diff_from_mean": "-41874.50"
  }
}
```

Field notes:
- **`stats`** is `null` when no fresh source has a usable price. All monetary
  values are strings (2 dp), like the rest of the feed.
- **`mean_2sigma` / `mean_3sigma`** are single-pass sigma-clipped means: drop
  values more than k·σ from the mean, then re-average. `count_Nsigma` is how many
  sources remained. With very few sources a lone outlier can inflate σ enough to
  survive (statistical masking) — expected behaviour.
- **`excluded_sources[].reason`** is `stale` (too old) or `no_price` (no usable
  quote).
- **`gerami`** is always present if Gerami has a row (even if stale/excluded);
  `included_in_stats` says whether it counted, and `diff_from_*` compares its mid
  to the market.

> Prefer `stats` when you want the market summary; `compare` when you want each
> source's row; `latest` for the full multi-asset dump.
