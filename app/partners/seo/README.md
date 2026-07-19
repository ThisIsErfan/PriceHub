# Partner module: `seo`

Serves the **SEO team**. Mounted at `/v1/seo`. Keys for this partner can only
call these routes (a `technical` key gets `403` here).

## Endpoints

| Method | Path | Scope | Returns |
|--------|------|-------|---------|
| GET | `/v1/seo/prices/latest` | `prices:read` | Latest platform price for the featured assets (`?asset=` to narrow) |
| GET | `/v1/seo/assets` | `prices:read` | Asset catalog (`?type=gold\|silver\|coin\|…`) |
| GET | `/v1/seo/news` | `news:read` | Recent metals news headlines (`?symbol=gold\|silver\|copper`, `?limit=1..50`) |

Featured assets are curated in [`service.py`](service.py) (`SEO_FEATURED_ASSETS`)
so the SEO feed stays focused on what they publish. Supplier quotes are excluded
from this feed by design (platform/reference prices only).

## Add / change SEO endpoints

Edit [`service.py`](service.py) (data logic, reusing `app/shared/data/`) and
[`router.py`](router.py) (routes). Keep every route GET and behind
`require_partner("seo", scope=…)`.
