"""API-key generation, hashing, and verification.

Deliberately dependency-free — standard library only (secrets, hashlib), same
spirit as the copilot backend's security module. Partner API keys are the sole
credential a partner holds, so they are treated like passwords:

  * The full key is shown to the partner **once**, at mint time. We never store
    it in cleartext.
  * The database stores only a SHA-256 `key_hash` (for lookup/verification) plus
    a short `key_prefix` (for human identification in listings/logs).

Key shape:

    ph_live_<43-char url-safe random>
    └──┬──┘ └────────────┬───────────┘
     prefix         256 bits of entropy

`ph_` brands it, `live` leaves room for a future `ph_test_` class. The whole
string is what the partner sends; the hash of the whole string is what we store.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

KEY_ENV = "live"
_KEY_BRAND = "ph"
# First N chars kept in cleartext purely for identification (never enough to use).
PREFIX_LEN = 16  # e.g. "ph_live_AbCdEf12"


def generate_api_key() -> str:
    """Return a fresh, high-entropy partner key: ``ph_live_<random>``."""
    return f"{_KEY_BRAND}_{KEY_ENV}_{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    """SHA-256 hex digest of the full key — what we store and compare against."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def key_prefix(key: str) -> str:
    """The identifying prefix stored alongside the hash (safe to display)."""
    return key[:PREFIX_LEN]


def verify_api_key(candidate: str, stored_hash: str) -> bool:
    """Constant-time check of a presented key against a stored SHA-256 hash."""
    return hmac.compare_digest(hash_api_key(candidate), stored_hash)
