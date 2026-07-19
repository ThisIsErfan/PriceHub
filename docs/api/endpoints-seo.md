# SEO partner endpoints

Base: `https://api.gerami.online/v1/seo`
Auth: `X-API-Key` for a key on partner `seo`.
All GET. See [responses.md](responses.md) for the envelope and full examples.

Served by the code module [`app/partners/seo/`](../../app/partners/seo/).

---

## GET /v1/seo/prices/latest

Latest **platform** price for the SEO featured assets (gold 18k/24k/melted/ounce,
silver, coins). Supplier quotes are excluded.

**Scope:** `prices:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `asset` | string | – | narrow to a single asset slug (e.g. `gold-18k`) |

```bash
curl -H "X-API-Key: $KEY" "https://api.gerami.online/v1/seo/prices/latest?asset=gold-18k"
```

`data`: `{ items: [ {asset, asset_title_fa, asset_title_en, unit, source, currency, price, crawled_at} ], count, generated_at }`

---

## GET /v1/seo/assets

The asset catalog you can reference (slugs, titles, units, purity).

**Scope:** `prices:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | – | filter by type: `gold`, `silver`, `coin`, `currency`, `crypto`, … |

```bash
curl -H "X-API-Key: $KEY" "https://api.gerami.online/v1/seo/assets?type=coin"
```

`data`: `{ items: [ {slug, symbol, title_en, title_fa, type, unit, purity} ] }`

---

## GET /v1/seo/news

Recent metals news headlines (title, summary, link, publisher, image,
published_at). Full article bodies are not exposed on this feed.

**Scope:** `news:read`

| Query | Type | Default | Description |
|-------|------|---------|-------------|
| `symbol` | string | – | filter by metal: `gold`, `silver`, `copper` |
| `limit` | int (1–50) | 20 | max articles |

```bash
curl -H "X-API-Key: $KEY" "https://api.gerami.online/v1/seo/news?symbol=gold&limit=10"
```

`data`: `{ items: [ {title, summary, url, publisher, image_url, published_at, source} ], count }`

---

## Featured asset list

The `prices/latest` feed is curated to the assets the SEO team publishes about,
defined in [`app/partners/seo/service.py`](../../app/partners/seo/service.py)
(`SEO_FEATURED_ASSETS`). To add/remove one, edit that list.
