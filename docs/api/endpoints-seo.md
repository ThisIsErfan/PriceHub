# SEO partner endpoints

Base: `https://api.gerami.online/v1/seo`
Auth: `X-API-Key` for a key on partner `seo` (scope `prices:read`).

`price-page` is the partner's **only** endpoint. Reference implementations of a
featured-price feed and a news feed live in
[`service.py`](../../app/partners/seo/service.py) — already on the shared
response standard — but are deliberately **not enabled**; enabling one means
adding a route in `router.py` and the matching scope on the key.

Responses follow the shared standard — see [responses.md](responses.md).

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
