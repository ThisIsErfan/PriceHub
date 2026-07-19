"""Partner registry.

Each partner is a self-contained code module under this package that exposes a
`router` (an APIRouter mounted at `/v1/<slug>`). To add a partner:

  1. create `app/partners/<slug>/` with a `router.py` defining `router` and a
     `SLUG` that matches the directory name;
  2. import it below and add it to `PARTNER_ROUTERS`;
  3. insert the matching `partners` row and mint a key (scoped to <slug>).

`app.main` mounts everything in `PARTNER_ROUTERS`. Keeping the list explicit
(rather than auto-discovering) means enabling a partner is a reviewable one-line
change, and nothing is ever served by accident.
"""

from app.partners.seo.router import router as seo_router
from app.partners.technical.router import router as technical_router

# (mount_path, router) — mount_path is the partner slug segment under /v1.
PARTNER_ROUTERS = [
    ("seo", seo_router),
    ("technical", technical_router),
]
