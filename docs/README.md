# PriceHub documentation

Docs are grouped by topic. If you are setting this up for the first time, start
with the **operations** guide — it's the from-zero checklist.

## Index

### architecture/
Understand the system before changing it.
- [overview.md](architecture/overview.md) — what PriceHub is, how the pieces fit, request lifecycle.
- [redis.md](architecture/redis.md) — exactly what Redis does (and does not) do here.

### api/
Everything a consumer of the API needs.
- [health.md](api/health.md) — public liveness (`/health`) & readiness (`/health/ready`) checks — probe before calling.
- [authentication.md](api/authentication.md) — API keys, the `X-API-Key` header, scopes, tenant isolation.
- [responses.md](api/responses.md) — the response envelope and example payloads per endpoint.
- [rate-limiting.md](api/rate-limiting.md) — the per-second / per-minute caps and the `429` behaviour.
- [errors.md](api/errors.md) — every error code, when it fires, and how to react.
- [endpoints-seo.md](api/endpoints-seo.md) — the `seo` partner's endpoints + sample responses.
- [endpoints-technical.md](api/endpoints-technical.md) — the `technical` partner's endpoints + sample responses.

### database/
- [schema.md](database/schema.md) — `partner_schm` tables, the `partner_api_usr` role, grants, and usage-reporting queries.

### operations/
- [setup-guide.md](operations/setup-guide.md) — **step-by-step**: server DB role, GitHub Actions secrets, VPS deploy, nginx/TLS, first keys.

### partners/
- [onboarding.md](partners/onboarding.md) — how to add a new partner and mint/rotate/revoke keys.

## Conventions used across the docs

- Base URL in production: `https://api.gerami.online`
- All **data** endpoints are **GET** and **versioned** under `/v1/<partner>/…`.
- Public, unauthenticated: `GET /health` and `GET /health/ready` — see [api/health.md](api/health.md).
- Every response uses the envelope `{success, message, responseCode, data}`.
- Auth is a single header: `X-API-Key: ph_live_…`.
