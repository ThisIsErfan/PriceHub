#!/usr/bin/env python3
"""Mint a partner API key: print the key ONCE, emit the INSERT SQL to store it.

The key itself is never persisted by this script and never stored in cleartext
anywhere — only its SHA-256 hash + prefix go into the DB. You hand the printed
key to the partner over a secure channel; if it is lost, mint a new one and
revoke the old.

Usage:
    python scripts/mint_api_key.py <partner_slug> --scopes prices:read,news:read \
        [--label "seo prod #1"] [--per-sec 5] [--per-min 120]

Then apply the emitted SQL against the crawler DB (as copilot_usr), e.g.:
    docker exec -e PGPASSWORD="$COPILOT_DB_PASSWORD" -i pricing-postgres-crawlers \
      psql -U copilot_usr -d pricing_db -v ON_ERROR_STOP=1 <<'SQL'
      <paste the INSERT here>
    SQL

The INSERT resolves partner_id from the slug, so the partner row (V001 seed or
your own) must exist first.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import generate_api_key, hash_api_key, key_prefix  # noqa: E402


def _sql_array(scopes: list[str]) -> str:
    """Render a Postgres text[] literal from scope strings."""
    inner = ",".join(s.replace("'", "''") for s in scopes)
    return "'{" + inner + "}'"


def main() -> None:
    parser = argparse.ArgumentParser(description="Mint a partner API key.")
    parser.add_argument("slug", help="partner slug (must match a partners.slug row)")
    parser.add_argument("--scopes", default="", help="comma-separated, e.g. prices:read,news:read")
    parser.add_argument("--label", default=None, help="human label for this key")
    parser.add_argument("--per-sec", type=int, default=None, help="override per-second rate limit")
    parser.add_argument("--per-min", type=int, default=None, help="override per-minute rate limit")
    args = parser.parse_args()

    scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]

    key = generate_api_key()
    khash = hash_api_key(key)
    kprefix = key_prefix(key)

    label_sql = "NULL" if not args.label else "'" + args.label.replace("'", "''") + "'"
    per_sec_sql = "NULL" if args.per_sec is None else str(args.per_sec)
    per_min_sql = "NULL" if args.per_min is None else str(args.per_min)

    insert = f"""INSERT INTO partner_schm.partner_api_keys
    (partner_id, label, key_prefix, key_hash, scopes, rate_limit_per_sec, rate_limit_per_min)
SELECT p.id, {label_sql}, '{kprefix}', '{khash}', {_sql_array(scopes)}, {per_sec_sql}, {per_min_sql}
FROM   partner_schm.partners p
WHERE  p.slug = '{args.slug}';"""

    print("=" * 72)
    print("  PARTNER API KEY — shown ONCE. Copy it now; it cannot be recovered.")
    print("=" * 72)
    print(f"  partner : {args.slug}")
    print(f"  scopes  : {', '.join(scopes) if scopes else '(none)'}")
    print(f"  prefix  : {kprefix}")
    print()
    print(f"  KEY: {key}")
    print()
    print("-" * 72)
    print("  Apply this SQL as copilot_usr to store the key (hash only):")
    print("-" * 72)
    print(insert)


if __name__ == "__main__":
    main()
