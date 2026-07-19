# Database — partner_schm

PriceHub adds one schema, **`partner_schm`**, inside the existing `pricing_db`
(the same database the crawlers and copilot backend use). It also adds one login
role, **`partner_api_usr`**. Nothing about the price/news data changes.

DDL lives in [`migrations/partner/`](../../migrations/partner/):
- `V001__partner_schm.sql` — schema + tables + seed partners.
- `R001__grants.sql` — the `partner_api_usr` role + grants (repeatable).

## Tables

### `partners`
One row per consumer we hand an API to.

| Column | Type | Notes |
|--------|------|-------|
| `id` | bigint PK | |
| `slug` | varchar unique | **must equal** `app/partners/<slug>/` (e.g. `seo`, `technical`) |
| `name` | varchar | display name |
| `contact` | varchar | who to reach |
| `status` | varchar | `active` \| `suspended` \| `disabled` — master switch |
| `notes` | text | |
| `created_at` / `updated_at` | timestamptz | |

Auth requires `status = 'active'`; flipping it cuts off all of a partner's keys.

### `partner_api_keys`
Credentials. The key itself is never stored — only its hash + prefix.

| Column | Type | Notes |
|--------|------|-------|
| `id` | bigint PK | |
| `partner_id` | bigint FK → partners | |
| `label` | varchar | e.g. `seo prod #1` |
| `key_prefix` | varchar | first chars, shown for identification (safe) |
| `key_hash` | varchar(64) unique | SHA-256 hex of the full key |
| `scopes` | text[] | e.g. `{prices:read,news:read}` |
| `rate_limit_per_sec` | int null | null → app default (5) |
| `rate_limit_per_min` | int null | null → app default (120) |
| `is_active` | bool | per-key on/off |
| `last_used_at` | timestamptz | touched on each use |
| `created_at` | timestamptz | |
| `revoked_at` | timestamptz | set to revoke this one key |

Auth looks a key up by `key_hash` among the active, non-revoked rows (partial
index `idx_partner_api_keys_active_hash`).

### `partner_usage_daily`
Durable request counting — the answer to "how many calls did partner X make".

| Column | Type | Notes |
|--------|------|-------|
| `api_key_id` | bigint FK → partner_api_keys | part of PK |
| `day` | date | part of PK |
| `endpoint` | varchar | route template, part of PK |
| `request_count` | bigint | incremented per request (UPSERT) |

One row per (key, day, endpoint) — bounded and tiny, unlike a per-request log.
The **real-time** per-second/minute rate-limit counters live in Redis, not here.

## Role & grants — `partner_api_usr`

The service connects as `partner_api_usr`, which can:

- **SELECT** on all `price_schm` + `news_schm` tables/views (the read feed), and
  on future tables there (via `ALTER DEFAULT PRIVILEGES`);
- **SELECT** on `partners` + `partner_api_keys` (auth lookups);
- **SELECT/INSERT/UPDATE** on `partner_usage_daily` (usage counting);
- **UPDATE** only `last_used_at` on `partner_api_keys` (column-level).

It **cannot** write price/news data, insert partners, or mint keys — so the
public-facing service has a tiny blast radius. The password is set at apply time
via a psql variable (kept out of git) and must match `PARTNER_DB_PASSWORD` in
pricing-copilot's `crawlers/.env`.

## Reporting queries

**Calls per partner, last 30 days:**
```sql
SELECT p.slug, SUM(u.request_count) AS calls
FROM   partner_schm.partner_usage_daily u
JOIN   partner_schm.partner_api_keys k ON k.id = u.api_key_id
JOIN   partner_schm.partners p         ON p.id = k.partner_id
WHERE  u.day >= CURRENT_DATE - INTERVAL '30 days'
GROUP  BY p.slug
ORDER  BY calls DESC;
```

**Per-endpoint breakdown for one partner today:**
```sql
SELECT u.endpoint, u.request_count
FROM   partner_schm.partner_usage_daily u
JOIN   partner_schm.partner_api_keys k ON k.id = u.api_key_id
JOIN   partner_schm.partners p         ON p.id = k.partner_id
WHERE  p.slug = 'seo' AND u.day = CURRENT_DATE
ORDER  BY u.request_count DESC;
```

**Active keys and when they were last used:**
```sql
SELECT p.slug, k.label, k.key_prefix, k.scopes, k.is_active, k.last_used_at
FROM   partner_schm.partner_api_keys k
JOIN   partner_schm.partners p ON p.id = k.partner_id
ORDER  BY p.slug, k.created_at;
```
