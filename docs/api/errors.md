# Errors

All errors use the standard envelope (`success:false`, `data` usually `null`) and
the HTTP status equals `responseCode`.

| Code | `message` (example) | When | What to do |
|------|---------------------|------|------------|
| `400` | Bad request | malformed request | fix the request |
| `401` | `API key required. Send it in the 'X-API-Key' header.` | no `X-API-Key` header | add the header |
| `401` | `Invalid or inactive API key.` | key unknown, `is_active=false`, revoked, or partner not `active` | check the key / partner status; mint a new key if needed |
| `403` | `This API key is not authorised for this partner's endpoints.` | key's partner ≠ the `/v1/<partner>/` you called | call your own partner's endpoints |
| `403` | `This API key lacks the scope required for this endpoint.` | scope check failed | request the needed scope on your key |
| `404` | Not Found | unknown path | check the URL/version |
| `422` | `Validation error` | bad query param (e.g. `limit` out of range) | see `data.errors`; fix the params |
| `429` | `Rate limit exceeded. Slow down and retry.` | per-second or per-minute cap hit | honour `Retry-After`, back off |
| `500` | `Internal server error` | unexpected server fault | retry later; report if it persists |

## Notes

- **401 vs 403** — `401` means "we don't know/accept who you are" (missing or
  invalid key). `403` means "we know you, but you may not do this" (wrong partner
  or missing scope).
- **429** always includes a `Retry-After` header (seconds). See
  [rate-limiting.md](rate-limiting.md).
- **422** includes the offending fields under `data.errors` (FastAPI validation
  detail).
