# SEO partner endpoints

Base: `https://api.gerami.online/v1/seo`
Auth: `X-API-Key` for a key on partner `seo`.
All responses follow the shared standard — nested `source`/`asset`/`currency`
refs, `bid`/`ask` quotes, `items` + `count` + `generated_at`. See
[responses.md](responses.md).

## Endpoints

- [GET /v1/seo/price-page](#get-price-page) — the talasea gold & coin tables (18k from gerami) · scope `prices:read`
- [GET /v1/seo/prices/latest](#get-priceslatest) — latest quote for the featured SEO assets · scope `prices:read`
- [GET /v1/seo/news](#get-news) — recent metals news headlines · scope `news:read`

---

## `GET /price-page`

The site's price page: every row of `seo_schm.talasea_gold_prices` (the gold and
coin tables scraped from talasea.ir/gold-price), latest snapshot only. Items are
returned in on-page order — the gold table first, then coins.

**Scope:** `prices:read`

### 18k gold is served from the Gerami source

For the `geram18` row (طلای ۱۸ عیار, one gram), the numeric fields are **rebuilt
from the Gerami source** — which is already crawled into `price_schm` — instead
of the talasea scrape:

| Field | Source for `geram18` |
|-------|----------------------|
| `current_price` | Gerami — latest 18k price |
| `low_price` / `high_price` | Gerami — min/max over the last 24h |
| `change_1d_percent` | Gerami — vs ~24h ago |
| `change_30d_percent` | Gerami — vs ~30d ago |
| `name`, `unit`, `category` | stored (talasea) — unchanged |
| `weekly_chart_path` | stored (talasea) — the sparkline is a talasea render, not in the gerami feed |

If Gerami has no 18k history (e.g. a fresh environment), the stored talasea
values are served unchanged and `gold_18k_source` reports `"talasea"`. Every
other row always comes from the talasea scrape.

### Response

Each item carries the standard `source` ref naming which producer it came from
(`gerami` for the 18k row, `talasea` for the rest). Its `category`/`slug`/`name`/
`unit` are the scraped page's own columns — not rows of the `assets`/
`currencies` catalogs — so there is no asset or currency ref on this endpoint.

```json
{
  "success": true,
  "message": "OK",
  "responseCode": 200,
  "data": {
    "items": [
      {
        "source": { "slug": "gerami", "title_fa": "گرمی", "title_en": "Gerami", "role": "platform" },
        "category": "gold",
        "slug": "geram18",
        "name": "طلای ۱۸ عیار",
        "unit": "تومان",
        "current_price": "18071900.0000",
        "low_price": "17900000.0000",
        "high_price": "18100000.0000",
        "change_1d_percent": "1.528",
        "change_30d_percent": "15.108",
        "weekly_chart_path": "M2,44...",
        "crawled_at": "2026-07-26T12:26:46.855151+00:00"
      }
    ],
    "count": 13,
    "gold_18k_source": "gerami",
    "generated_at": "2026-07-26T12:30:00.000000+00:00"
  }
}
```

Prices/percentages are exact decimal **strings** (never floats — see
[responses.md](responses.md)).

### Example

```bash
curl -H "X-API-Key: $SEO_KEY" https://api.gerami.online/v1/seo/price-page
```

---

## `GET /prices/latest`

Latest quote for the assets the SEO team writes about — 18k/24k/melted gold,
gold & silver ounce, silver 999, and the four coins — from platform and
reference sources only (supplier quotes are excluded).

**Scope:** `prices:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `asset` | string | – | limit to one asset slug (e.g. `gold-18k`); omit for the whole featured set |

```bash
curl -H "X-API-Key: $SEO_KEY" "https://api.gerami.online/v1/seo/prices/latest?asset=gold-18k"
```

`data`:
```json
{
  "items": [
    {
      "source":   { "slug": "gerami", "title_fa": "گرمی", "title_en": "Gerami", "role": "platform" },
      "asset":    { "slug": "gold-18k", "symbol": "GOLD_18K", "std_symbol": "XAU750g",
                    "title_fa": "طلای ۱۸ عیار", "title_en": "Gold 18K", "type": "gold", "unit": "gram" },
      "currency": { "code": "IRT", "title_fa": "تومان ایران", "title_en": "Iranian Toman", "type": "fiat" },
      "is_single_rate": true,
      "bid": "18453900.00000000",
      "ask": "18453900.00000000",
      "crawled_at": "2026-07-19T08:41:12+00:00"
    }
  ],
  "count": 1,
  "generated_at": "2026-07-19T08:41:20.123456+00:00"
}
```

Most SEO sources publish a single number rather than a buy/sell split, so it is
reported as `bid == ask` with `is_single_rate: true` — **for display, read
`ask`** (فروش).

---

## `GET /news`

Recent metals news headlines (title, summary, link, publisher, image, published
date). Article bodies are not exposed.

**Scope:** `news:read` — a key with only `prices:read` gets `403`.

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `symbol` | string | – | filter by metal symbol slug: `gold`, `silver`, `copper` |
| `limit` | int (1–50) | `20` | how many articles |

```bash
curl -H "X-API-Key: $SEO_KEY" "https://api.gerami.online/v1/seo/news?symbol=gold&limit=10"
```

`data`: `{ items: [ {source, title, summary, url, publisher, image_url, published_at} ], count, generated_at }`

`source` is the news-feed ref — `{slug, title_fa, title_en, type}` — see
[responses.md](responses.md).
