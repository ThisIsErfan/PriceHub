# Response format

Every response — success or error — uses one envelope:

```json
{
  "success": true,
  "message": "OK",
  "responseCode": 200,
  "data": { }
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `success` | bool | `true` on 2xx, `false` on any error |
| `message` | string | human-readable status / error text |
| `responseCode` | int | mirrors the HTTP status code |
| `data` | object / null | the payload (shape depends on the endpoint) |

The HTTP status code always equals `responseCode`, so clients can branch on either.

## Success payload shapes

Most data endpoints return a list under `data.items` plus a `count`. Timestamps
are ISO-8601 UTC. Prices are numeric strings/numbers exactly as stored (no
rounding).

### Example — `GET /v1/seo/prices/latest`

```json
{
  "success": true,
  "message": "OK",
  "responseCode": 200,
  "data": {
    "items": [
      {
        "asset": "gold-18k",
        "asset_title_fa": "طلای ۱۸ عیار",
        "asset_title_en": "Gold 18K",
        "unit": "per_gram",
        "source": "gerami",
        "currency": "IRR",
        "price": "38250000.00000000",
        "crawled_at": "2026-07-19T08:41:12.000000+00:00"
      }
    ],
    "count": 1,
    "generated_at": "2026-07-19T08:41:20.123456+00:00"
  }
}
```

### Example — `GET /v1/technical/prices/platforms/latest`

Nested `source`/`asset`/`currency` + `is_single_rate`. Quotes are `bid`/`ask`
only (no bare `price`; a single-rate source reports `bid == ask`). Each asset
carries `std_symbol` (standard metal code, `null` when absent).

```json
{
  "success": true,
  "message": "OK",
  "responseCode": 200,
  "data": {
    "items": [
      {
        "source":   { "slug": "gerami", "title_en": "Gerami", "title_fa": "گرمی" },
        "asset":    { "slug": "gold-18k", "symbol": "GOLD_18K", "std_symbol": "XAU", "title_fa": "طلای ۱۸ عیار", "unit": "per_gram" },
        "currency": { "code": "IRT", "title_fa": "تومان" },
        "is_single_rate": false,
        "bid": "3820000.00000000",
        "ask": "3830000.00000000",
        "crawled_at": "2026-07-19T08:41:12+00:00"
      }
    ],
    "count": 1,
    "generated_at": "2026-07-19T08:41:20.123456+00:00"
  }
}
```

### Example — `GET /v1/technical/prices/suppliers/latest`

```json
{
  "data": {
    "items": [
      {
        "supplier": "zariran",
        "supplier_title_fa": "زر ایران",
        "asset": "gold-18k",
        "std_symbol": "XAU",
        "unit": "per_gram",
        "currency": "IRR",
        "buy_price": "38100000.00000000",
        "sell_price": "38300000.00000000",
        "crawled_at": "2026-07-19T08:41:10.000000+00:00"
      }
    ],
    "count": 1
  }
}
```

### Example — `GET /v1/seo/news`

```json
{
  "data": {
    "items": [
      {
        "title": "Gold edges higher as ...",
        "summary": "Spot gold rose ...",
        "url": "https://finance.yahoo.com/news/...",
        "publisher": "Reuters",
        "image_url": "https://.../thumb.jpg",
        "published_at": "2026-07-19T07:30:00+00:00",
        "source": "yahoo_finance_metals"
      }
    ],
    "count": 1
  }
}
```

## Error payload

```json
{
  "success": false,
  "message": "Invalid or inactive API key.",
  "responseCode": 401,
  "data": null
}
```

Validation errors (`422`) carry details:

```json
{
  "success": false,
  "message": "Validation error",
  "responseCode": 422,
  "data": { "errors": [ { "loc": ["query", "limit"], "msg": "...", "type": "..." } ] }
}
```

See [errors.md](errors.md) for the full code list.
