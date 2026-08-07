import base64
import hashlib
import secrets
import time
import uuid
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

# Tuned Argon2id parameters (OWASP-recommended floor for interactive login:
# >= 19 MiB memory, t=2, p=1 — we go higher since this runs server-side only).
_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _password_hasher.check_needs_rehash(password_hash)


def generate_opaque_token() -> str:
    """A high-entropy, URL-safe token for refresh tokens and single-use links."""
    return secrets.token_urlsafe(32)


def generate_pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge) for an OAuth Authorization Code + PKCE flow."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def hash_token(token: str) -> str:
    """SHA-256 of an opaque token — what we store, never the raw token itself."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


TokenType = Literal["access"]


def create_access_token(*, user_id: uuid.UUID, role: str) -> tuple[str, int]:
    settings = get_settings()
    now = int(time.time())
    expires_in = settings.access_token_ttl_minutes * 60
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + expires_in,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm)
    return token, expires_in


class InvalidAccessTokenError(Exception):
    pass


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise InvalidAccessTokenError(str(exc)) from exc

    if payload.get("type") != "access":
        raise InvalidAccessTokenError("not an access token")

    return payload
