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

> **Note:** only the two endpoints above are exposed. Catalog endpoints
> (`/sources`, `/assets`) are not part of the technical surface for now; the
> `reference:read` scope is unused until/unless they are added back.
