"""Private link tokens for customers (proposal links and work-order links).

The raw token is shown once (in the link we hand to the estimator); the database only
stores its SHA-256 hash, so a leaked database cannot be turned back into working links.
"""

import hashlib
import secrets


def new_token() -> str:
    """A high-entropy, URL-safe token (32 random bytes, ~43 characters)."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
