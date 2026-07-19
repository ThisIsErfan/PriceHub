# Partner module: `seo`

Serves the **SEO team**. Mounted at `/v1/seo`. Keys for this partner can only
call this namespace (a `technical` key gets `403` here).

## Status: no endpoints yet

The SEO surface is intentionally **empty for now** — routes will be defined later.
[`router.py`](router.py) has no routes, so `/v1/seo/*` returns `404` until they
are added.

A reference implementation (featured prices, news, assets catalog) is preserved
in [`service.py`](service.py) to draw from when wiring endpoints up:
`SEO_FEATURED_ASSETS` curates the assets the SEO team publishes about, and
supplier quotes are excluded (platform/reference prices only).

## Add / change SEO endpoints

Edit [`service.py`](service.py) (data logic, reusing `app/shared/data/`) and
[`router.py`](router.py) (routes). Keep every route GET and behind
`require_partner("seo", scope=…)`.
