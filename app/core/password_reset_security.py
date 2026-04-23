import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


RESET_TOKEN_BYTES = 32
RESET_TOKEN_MIN_LENGTH = 40
RESET_TOKEN_TTL_MINUTES = 10


def now_utc():
    return datetime.now(timezone.utc)


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def generate_reset_token() -> str:
    return secrets.token_urlsafe(RESET_TOKEN_BYTES)


def hash_reset_token(token: str) -> str:
    token = (token or "").strip()
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_expiry():
    return now_utc() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)


def is_token_format_valid(token: str) -> bool:
    token = (token or "").strip()
    return len(token) >= RESET_TOKEN_MIN_LENGTH


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a or "", b or "")


def is_expired(expires_at) -> bool:
    if expires_at is None:
        return True

    if getattr(expires_at, "tzinfo", None) is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return now_utc() > expires_at