"""Password hashing and session tokens. Small enough to read in one go."""

from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()

MIN_PASSWORD_LENGTH = 8


class WeakPassword(Exception):
    pass


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPassword(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def new_session_token() -> str:
    """Opaque token; the database stores only its hash."""
    return secrets.token_urlsafe(40)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_invite_code() -> str:
    return secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:10].upper()
