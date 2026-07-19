-- =============================================================================
-- partner/V001__partner_schm.sql
--
-- Creates the partner_schm schema and its three tables inside the EXISTING
-- pricing_db (same database the crawlers + copilot backend use). Owned by
-- copilot_usr so that copilot_usr's ALTER DEFAULT PRIVILEGES and the app roles'
-- grants behave consistently with the rest of the DB.
--
-- Apply as the owner (copilot_usr) against the running crawler DB:
--   docker exec -i pricing-postgres-crawlers \
--     psql -U copilot_usr -d pricing_db -v ON_ERROR_STOP=1 \
--     < migrations/partner/V001__partner_schm.sql
--
-- Then run R001__grants.sql to create/grant the partner_api_usr login role.
--
-- Pure SQL only (no psql backslash meta-commands beyond \connect) so it also
-- runs through a plain psycopg2 migration runner if you wire one up later.
-- =============================================================================

\connect pricing_db

CREATE SCHEMA IF NOT EXISTS "partner_schm" AUTHORIZATION "copilot_usr";

SET search_path TO "partner_schm", public;

-- -----------------------------------------------------------------------------
-- partners
-- One row per consumer we hand an API to. `slug` MUST match a partner code
-- module directory under app/partners/<slug>/ (e.g. 'seo', 'technical'); the
-- auth layer ties every key to its partner's slug so a key can only call its own
-- module. `status` is the master switch: flip to 'suspended'/'disabled' to cut a
-- partner off across all their keys instantly (auth checks status = 'active').
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "partners" (
    "id"          BIGINT       PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "slug"        VARCHAR(64)  NOT NULL UNIQUE,          -- == app/partners/<slug>
    "name"        VARCHAR(225) NOT NULL,                 -- human/display name
    "contact"     VARCHAR(225) DEFAULT NULL,             -- who to reach (email/phone/team)
    "status"      VARCHAR(16)  NOT NULL DEFAULT 'active',-- active | suspended | disabled
    "notes"       TEXT         DEFAULT NULL,
    "created_at"  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    "updated_at"  TIMESTAMPTZ  DEFAULT NULL,
    CONSTRAINT partners_status_chk CHECK (status IN ('active', 'suspended', 'disabled'))
);

-- -----------------------------------------------------------------------------
-- partner_api_keys
-- The credentials. We store only a SHA-256 hash of the key plus a short,
-- non-secret prefix for identification (see app/core/security.py). One partner
-- may hold several keys (rotation, per-environment). Per-key rate limits default
-- to NULL → the app falls back to its configured defaults
-- (DEFAULT_RATE_LIMIT_PER_SEC / _MIN); set a number here to override one key.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "partner_api_keys" (
    "id"                 BIGINT       PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "partner_id"         BIGINT       NOT NULL REFERENCES "partners" ("id") ON DELETE CASCADE,
    "label"              VARCHAR(128) DEFAULT NULL,      -- e.g. 'seo prod key #1'
    "key_prefix"         VARCHAR(32)  NOT NULL,          -- shown for identification (safe)
    "key_hash"           VARCHAR(64)  NOT NULL UNIQUE,   -- SHA-256 hex of the full key
    "scopes"             TEXT[]       NOT NULL DEFAULT '{}',  -- e.g. {prices:read,news:read}
    "rate_limit_per_sec" INTEGER      DEFAULT NULL,      -- NULL → app default
    "rate_limit_per_min" INTEGER      DEFAULT NULL,      -- NULL → app default
    "is_active"          BOOLEAN      NOT NULL DEFAULT TRUE,
    "last_used_at"       TIMESTAMPTZ  DEFAULT NULL,
    "created_at"         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    "revoked_at"         TIMESTAMPTZ  DEFAULT NULL       -- set to revoke this one key
);

CREATE INDEX IF NOT EXISTS idx_partner_api_keys_partner ON "partner_api_keys" ("partner_id");
-- Auth looks keys up by hash among the active ones — keep that path indexed.
CREATE INDEX IF NOT EXISTS idx_partner_api_keys_active_hash
    ON "partner_api_keys" ("key_hash") WHERE is_active = TRUE AND revoked_at IS NULL;

-- -----------------------------------------------------------------------------
-- partner_usage_daily
-- Durable request counting — the answer to "how many calls did partner X make".
-- One row per (key, day, endpoint), incremented per request by the app
-- (app/usage/recorder.py). Bounded by keys × days × endpoints, so it never
-- balloons the way a per-request log would. The real-time per-minute/second
-- rate-limit counters live in Redis, NOT here.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "partner_usage_daily" (
    "api_key_id"    BIGINT      NOT NULL REFERENCES "partner_api_keys" ("id") ON DELETE CASCADE,
    "day"           DATE        NOT NULL,
    "endpoint"      VARCHAR(255) NOT NULL,               -- route template, e.g. /v1/seo/prices/latest
    "request_count" BIGINT      NOT NULL DEFAULT 0,
    PRIMARY KEY ("api_key_id", "day", "endpoint")
);

CREATE INDEX IF NOT EXISTS idx_partner_usage_day ON "partner_usage_daily" ("day");

-- Ownership (belt-and-suspenders; CREATE ... AUTHORIZATION already set schema owner).
ALTER TABLE "partners"            OWNER TO "copilot_usr";
ALTER TABLE "partner_api_keys"    OWNER TO "copilot_usr";
ALTER TABLE "partner_usage_daily" OWNER TO "copilot_usr";

-- -----------------------------------------------------------------------------
-- Seed the two internal partners (idempotent). Keys are minted separately with
-- scripts/mint_api_key.py — no secrets live in this migration.
-- -----------------------------------------------------------------------------
INSERT INTO "partners" (slug, name, contact, notes) VALUES
    ('seo',       'SEO Team (internal)',       'internal', 'Price/news feed for SEO content.'),
    ('technical', 'Technical Team (internal)', 'internal', 'Raw price/supplier data for integrations.')
ON CONFLICT (slug) DO NOTHING;
