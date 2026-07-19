"""SEO partner endpoints — mounted at /v1/seo by app.main.

No endpoints are exposed yet: the SEO surface is intentionally left empty until
its requirements are defined. The partner, its key, and this namespace stay in
place, so adding routes later is purely additive (define them here, behind
`require_partner("seo", scope=…)`).

A reference implementation of price/news/asset routes for SEO is kept in
`service.py` for when we wire them up — see the module README.
"""

from __future__ import annotations

from fastapi import APIRouter

SLUG = "seo"
router = APIRouter(tags=["seo"])

# Endpoints intentionally omitted for now. Any request under /v1/seo/* therefore
# returns 404 until routes are added here.
