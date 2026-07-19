# Technical partner endpoints

Base: `https://api.gerami.online/v1/technical`
Auth: `X-API-Key` for a key on partner `technical`.
All GET. See [responses.md](responses.md) for the envelope and full examples.

Served by the code module [`app/partners/technical/`](../../app/partners/technical/).
This feed returns fuller rows than `seo` (every source, bid/ask, supplier quotes)
for machine integration.

---

## GET /v1/technical/prices/latest

Latest quote for **every** (source, asset, currency), including `bid`/`ask`.

**Scope:** `prices:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | string | – | filter by source slug (e.g. `tgju`, `nobitex`) |
| `asset` | string | – | filter by asset slug (e.g. `gold-ounce`) |
| `currency` | string | – | filter by currency code (e.g. `IRR`, `USD`) |
| `type` | string | – | filter by asset type (e.g. `gold`, `currency`, `crypto`) |

```bash
curl -H "X-API-Key: $KEY" \
  "https://api.gerami.online/v1/technical/prices/latest?asset=gold-ounce&currency=USD"
```

`data`: `{ items: [ {source, source_role, asset, asset_symbol, asset_type, unit, currency, price, bid, ask, crawled_at} ], count, generated_at }`

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

## GET /v1/technical/sources

The source catalog (data providers).

**Scope:** `reference:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `role` | string | – | filter by role: `platform`, `reference`, `supplier` |

`data`: `{ items: [ {slug, title_en, title_fa, type, role, url} ] }`

---

## GET /v1/technical/assets

The asset catalog.

**Scope:** `reference:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | – | filter by asset type |

`data`: `{ items: [ {slug, symbol, title_en, title_fa, type, unit, purity} ] }`
