# Deploy — PriceHub

Same CI/CD shape as pricing-copilot: **build in GitHub Actions → push to GHCR →
pull on the server.** No building on the VPS.

- **One image**: `ghcr.io/<owner>/pricehub` (FastAPI app), built by
  [`build-pricehub.yml`](../.github/workflows/build-pricehub.yml) on push to `main`.
- **One stack**: [`compose.pricehub.prod.yml`](compose.pricehub.prod.yml) —
  `pricehub` (the API) + `pricehub-redis`. It joins the **external** `pricing-net`
  (owned by pricing-copilot's crawler stack) and reaches Postgres by service name.
- **Deploy** with [`deploy-pricehub.yml`](../.github/workflows/deploy-pricehub.yml)
  (manual `workflow_dispatch`): scp the compose file, write `.env` from
  secrets/vars, `compose pull && up -d`. Target dir on the VPS: `~/pricehub`.

## Prerequisites on the server

1. The pricing-copilot **crawler stack is already running** (it owns `pricing-net`
   and `postgres-crawlers`).
2. The **`partner_api_usr` role + `partner_schm`** exist — apply
   [`../migrations/partner/V001__partner_schm.sql`](../migrations/partner/V001__partner_schm.sql)
   then [`R001__grants.sql`](../migrations/partner/R001__grants.sql). See the
   step-by-step [operations guide](../docs/operations/setup-guide.md).

## GitHub configuration (repo: PriceHub)

Secrets that gate prod live under **Settings → Environments → `prod`**.

**Server / SSH (secrets)** — reuse the same VPS values as pricing-copilot
| name | value |
|------|-------|
| `VPS_HOST` | server IP / hostname |
| `VPS_USER` | deploy user |
| `VPS_SSH_PASSWORD` | that user's password |
| `VPS_SSH_PORT` | optional, defaults to 22 |

**GHCR pull (secrets)** — a PAT with `read:packages`
| name | value |
|------|-------|
| `GHCR_USERNAME` | GitHub username owning the PAT |
| `GHCR_TOKEN` | the PAT |

**PriceHub (secrets)**
| name | value |
|------|-------|
| `PARTNER_DB_USER` | `partner_api_usr` (matches crawlers/.env) |
| `PARTNER_DB_PASSWORD` | the partner role password (matches crawlers/.env + R001) |
| `PRICEHUB_REDIS_PASSWORD` | `openssl rand -hex 32` |

**PriceHub (vars — optional)**
| name | value |
|------|-------|
| `PARTNER_CORS_ORIGINS` | usually empty (server-to-server) |
| `DEFAULT_RATE_LIMIT_PER_SEC` | default `5` |
| `DEFAULT_RATE_LIMIT_PER_MIN` | default `120` |

All PriceHub-specific names are prefixed `PARTNER_*` / `PRICEHUB_*`, and they
live in a **separate repo** from pricing-copilot — so nothing collides with the
copilot backend's secrets.

## How to deploy

1. Push to `main` → `build-pricehub.yml` builds & pushes the image (or run it
   manually from the Actions tab).
2. **Actions → "Deploy PriceHub (prod)" → Run workflow** (optionally pin
   `image_tag` to `git-<sha>`; default `latest`).
3. Add the `api.gerami.online` server block to your TLS reverse proxy →
   `proxy_pass http://127.0.0.1:8100;` (DNS already points there).

Roll back by re-running the deploy with `image_tag = git-<older-sha>`.

## Notes

- **Port** `127.0.0.1:8100` (8000/8081/8082/8090 are taken by copilot/airflow/
  charts). Never expose it publicly except through the TLS proxy.
- **Redis** has no host port and is password-protected; it is reachable only by
  `pricehub` over `pricing-net`. `maxmemory 128mb` + `allkeys-lru` cap its
  footprint; counters are ephemeral so persistence is disabled.
