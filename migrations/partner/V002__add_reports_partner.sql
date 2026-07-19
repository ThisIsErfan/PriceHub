-- =============================================================================
-- partner/V002__add_reports_partner.sql
--
-- Adds the third partner section, `reports` — the competitive/management report
-- feed consumed by an Airflow DAG that posts to a private Telegram channel.
-- Idempotent; apply as copilot_usr on the running DB:
--   docker exec -e PGPASSWORD="$COPILOT_DB_PASSWORD" -i pricing-postgres-crawlers \
--     psql -U copilot_usr -d pricing_db -v ON_ERROR_STOP=1 \
--     < migrations/partner/V002__add_reports_partner.sql
-- Then mint a key:  python scripts/mint_api_key.py reports --scopes reports:read
-- =============================================================================

\connect pricing_db

INSERT INTO "partner_schm"."partners" (slug, name, contact, notes) VALUES
    ('reports', 'Management Reports (internal)', 'internal',
     'Competitive price report feed (Gerami vs platforms) for the Telegram DAG.')
ON CONFLICT (slug) DO NOTHING;
