# SEO partner endpoints

Base: `https://api.gerami.online/v1/seo`
Auth: `X-API-Key` for a key on partner `seo`.

## Status: no endpoints yet

The SEO surface is intentionally **empty for now** — its endpoints will be
defined later once the requirements are set. The `seo` partner, its API key, and
the `/v1/seo` namespace already exist, so adding routes later is purely additive.

Any request under `/v1/seo/*` currently returns **404** (with a valid `seo` key)
or **401/403** first if the key is missing or belongs to another partner.

## Adding SEO endpoints later

1. Define routes in [`app/partners/seo/router.py`](../../app/partners/seo/router.py),
   each behind `require_partner("seo", scope=…)`.
2. A reference implementation (featured prices, news, assets) is preserved in
   [`app/partners/seo/service.py`](../../app/partners/seo/service.py) to draw from.
3. Update this doc with the concrete endpoints and sample responses.
