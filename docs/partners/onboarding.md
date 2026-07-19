# Partner onboarding & key management

How to add a partner, mint/rotate/revoke keys, and control access.

## Add a new partner

A partner is a **code module** + a **DB row**.

**1. Code** — create the module under `app/partners/<slug>/`:
```
app/partners/<slug>/
  __init__.py
  router.py     # APIRouter `router`, routes behind require_partner("<slug>", scope=...)
  service.py    # data logic, reusing app/shared/data/
  README.md
```
Copy [`app/partners/seo/`](../../app/partners/seo/) as a template. Keep every
route **GET**.

**2. Register** it in [`app/partners/__init__.py`](../../app/partners/__init__.py):
```python
from app.partners.<slug>.router import router as <slug>_router
PARTNER_ROUTERS = [
    ...,
    ("<slug>", <slug>_router),
]
```
It is now mounted at `/v1/<slug>`.

**3. DB row** — insert the partner (slug must match the directory):
```sql
INSERT INTO partner_schm.partners (slug, name, contact, notes)
VALUES ('<slug>', 'Display Name', 'contact', 'what they get')
ON CONFLICT (slug) DO NOTHING;
```

**4. Deploy** the new code (push → build → deploy) and **mint a key** (below).

> The two internal partners (`seo`, `technical`) are seeded by
> `V001__partner_schm.sql`, so for them you only mint keys.

## Mint a key

```bash
python3 scripts/mint_api_key.py <slug> --scopes prices:read,news:read \
    --label "descriptive label" [--per-sec N] [--per-min N]
```

The script prints:
- the **full key** — shown once, hand it to the partner over a secure channel;
- an **INSERT** that stores only the hash + prefix. Apply it as `copilot_usr`.

The key is never stored in cleartext and cannot be recovered — if lost, mint a new
one and revoke the old.

### Scopes

Mint with the scopes the partner needs (see
[../api/authentication.md](../api/authentication.md)):
`prices:read`, `news:read`, `reference:read`. Scope checks are relaxed while
consumers are internal, but minting with the right scopes now makes tightening
later a no-op.

### Per-key rate limits

Omit `--per-sec/--per-min` to use the app defaults (5/s, 120/min). Pass them to
override for a specific key, or change later:
```sql
UPDATE partner_schm.partner_api_keys
SET    rate_limit_per_min = 300
WHERE  key_prefix = 'ph_live_AbCdEf12';
```

## Rotate a key

1. Mint a new key for the same partner.
2. Give it to the partner; let them switch.
3. Revoke the old one:
```sql
UPDATE partner_schm.partner_api_keys
SET    revoked_at = NOW(), is_active = FALSE
WHERE  key_prefix = 'ph_live_OLDPREFIX';
```

## Revoke access

**One key:**
```sql
UPDATE partner_schm.partner_api_keys
SET    revoked_at = NOW(), is_active = FALSE
WHERE  key_prefix = 'ph_live_...';
```

**A whole partner** (all their keys at once):
```sql
UPDATE partner_schm.partners SET status = 'suspended' WHERE slug = '<slug>';
```
Set `status = 'active'` to restore. Both take effect on the next request (auth is
checked per request; no cache to wait on).

## See who has access / how much they use

```sql
-- keys per partner
SELECT p.slug, k.label, k.key_prefix, k.scopes, k.is_active, k.last_used_at
FROM   partner_schm.partner_api_keys k
JOIN   partner_schm.partners p ON p.id = k.partner_id
ORDER  BY p.slug;

-- calls per partner, last 30 days
SELECT p.slug, SUM(u.request_count) AS calls
FROM   partner_schm.partner_usage_daily u
JOIN   partner_schm.partner_api_keys k ON k.id = u.api_key_id
JOIN   partner_schm.partners p         ON p.id = k.partner_id
WHERE  u.day >= CURRENT_DATE - INTERVAL '30 days'
GROUP  BY p.slug ORDER BY calls DESC;
```

More reporting queries in [../database/schema.md](../database/schema.md).
