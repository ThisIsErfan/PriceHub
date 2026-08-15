# PriceHub

Partner-facing **read-only API** for the Gerami pricing data. Serves
`https://api.gerami.online/v1/…` to internal teams (SEO, technical) — and later
external partners — with per-key authentication, per-partner rate limits, and
durable per-partner usage tracking.

It is a **separate service** from `pricing-copilot`: its own repo, image,
workflows, secrets, and domain. It reads the **same** crawler database
(`pricing_db`) as a dedicated, SELECT-only role (`partner_api_usr`) and never
writes price/news data.

```
Internet ──TLS──▶ api.gerami.online ──▶ 127.0.0.1:8100 (pricehub)
                                              │  partner_api_usr (SELECT only)
                                              ▼
                            pricing-postgres-crawlers (pricing_db) ◀── crawlers write
                                              ▲
                            pricehub-redis ───┘  rate-limit windows + counters
```

## Key ideas

- **Per-partner code modules.** Each partner has its own directory under
  [`app/partners/`](app/partners/) with its own endpoints, SQL, and docs. A key
  scoped to partner `seo` can only call `/v1/seo/*` (a key for `technical` gets
  `403` there). Adding a partner = new directory + one `partners` row + a minted
  key.
- **API keys are hashed** (SHA-256) in `partner_schm.partner_api_keys`. The full
  key is shown **once** at mint time. Partners send it in the `X-API-Key` header
  (never the query string).
- **Redis enforces rate limits** (per-second + per-minute, per key) and holds
  ephemeral counters. **Postgres holds the durable truth** — every request is
  rolled up into `partner_schm.partner_usage_daily`, which answers "how many
  calls did partner X make."
- **Uniform envelope.** Every response is
  `{success, message, responseCode, data}` — same shape as the copilot API.

## Documentation

Everything is under [`docs/`](docs/), grouped by topic:

| Area | Start here |
|------|------------|
| Architecture & Redis role | [docs/architecture/](docs/architecture/) |
| **Every endpoint on one page** | [docs/api/endpoints.md](docs/api/endpoints.md) |
| API (auth, responses, errors, rate limits, per-partner endpoints) | [docs/api/](docs/api/) |
| Database (partner_schm, roles, grants) | [docs/database/](docs/database/) |
| **Step-by-step setup** (server + GitHub Actions + VPS + nginx) | [docs/operations/setup-guide.md](docs/operations/setup-guide.md) |
| Partner onboarding & key minting | [docs/partners/](docs/partners/) |

New here? Read [docs/operations/setup-guide.md](docs/operations/setup-guide.md)
top to bottom — it is the "from zero" checklist.

## Repo layout

```
app/                     FastAPI service
  core/                  config, api-key security, redis client
  db/                    async engine (partner_api_usr)
  api/deps.py            X-API-Key auth → resolves partner + scope
  usage/                 ratelimit (Redis) + recorder (durable counts)
  shared/                response envelope + reusable data queries
  partners/<slug>/       one directory PER PARTNER (router + service + README)
migrations/partner/      partner_schm tables + role grants (apply on the server)
scripts/mint_api_key.py  generate a key, print it once, emit INSERT SQL
deploy/                  prod compose (pricehub + redis) + env example + README
.github/workflows/       build-pricehub / deploy-pricehub
docs/                    all documentation, grouped by topic
```
