from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import UserRole
from app.core.errors import (
    AccountLockedError,
    ConflictError,
    NotConfiguredError,
    UnauthorizedError,
)
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    generate_pkce_pair,
    hash_password,
    hash_token,
    verify_password,
)
from app.integrations.email import send_email
from app.integrations.google_oauth import (
    GoogleOAuthError,
    build_authorization_url,
    exchange_code_for_userinfo,
)
from app.modules.users.models import RefreshToken, User
from app.modules.users.repository import RefreshTokenRepository, UserRepository

LOCKOUT_THRESHOLD = 5
LOCKOUT_BASE_MINUTES = 1
LOCKOUT_MAX_MINUTES = 60

EMAIL_VERIFY_TTL_SECONDS = 24 * 60 * 60
PASSWORD_RESET_TTL_SECONDS = 60 * 60
GOOGLE_OAUTH_STATE_TTL_SECONDS = 10 * 60

_EMAIL_VERIFY_PREFIX = "auth:email-verify:"
_PASSWORD_RESET_PREFIX = "auth:password-reset:"
_GOOGLE_OAUTH_STATE_PREFIX = "auth:google-oauth-state:"


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    expires_in: int
    refresh_token: str
    refresh_expires_at: datetime


class AuthService:
    def __init__(self, session: AsyncSession, redis: Redis[str]) -> None:
        self.session = session
        self.redis = redis
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def register(self, *, email: str, password: str, full_name: str) -> User:
        normalized_email = email.lower()
        if await self.users.get_by_email(normalized_email) is not None:
            raise ConflictError("An account with this email already exists.")

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=UserRole.SEEKER,
        )
        await self.users.create(user)
        await self._send_verification_email(user)
        return user

    async def authenticate(self, *, email: str, password: str) -> User:
        user = await self.users.get_by_email(email.lower())
        if user is None or user.password_hash is None:
            raise UnauthorizedError("Incorrect email or password.")

        now = datetime.now(UTC)
        if user.locked_until is not None and user.locked_until > now:
            retry_seconds = int((user.locked_until - now).total_seconds())
            raise AccountLockedError(
                "Too many failed attempts. Try again later.",
                retry_after=retry_seconds,
            )

        if not verify_password(password, user.password_hash):
            await self._register_failed_login(user)
            raise UnauthorizedError("Incorrect email or password.")

        if user.failed_login_attempts > 0 or user.locked_until is not None:
            user.failed_login_attempts = 0
            user.locked_until = None
            await self.session.flush()

        return user

    async def _register_failed_login(self, user: User) -> None:
        # Commit explicitly: the caller raises UnauthorizedError right after
        # this, and get_db_session rolls back on any exception, which would
        # otherwise silently erase the failed-attempt counter every time.
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= LOCKOUT_THRESHOLD:
            backoff_steps = user.failed_login_attempts - LOCKOUT_THRESHOLD
            minutes = min(LOCKOUT_BASE_MINUTES * (2**backoff_steps), LOCKOUT_MAX_MINUTES)
            user.locked_until = datetime.now(UTC) + timedelta(minutes=minutes)
        await self.session.commit()

    async def issue_token_pair(self, user: User) -> TokenPair:
        access_token, expires_in = create_access_token(user_id=user.id, role=user.role.value)

        settings = get_settings()
        raw_refresh = generate_opaque_token()
        refresh_expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)

        await self.refresh_tokens.create(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(raw_refresh),
                family_id=uuid.uuid4(),
                expires_at=refresh_expires_at,
            )
        )
        return TokenPair(access_token, expires_in, raw_refresh, refresh_expires_at)

    async def rotate_refresh_token(self, raw_refresh_token: str) -> tuple[User, TokenPair]:
        token_hash = hash_token(raw_refresh_token)
        existing = await self.refresh_tokens.get_by_hash(token_hash)
        if existing is None:
            raise UnauthorizedError("Invalid refresh token.")

        now = datetime.now(UTC)

        if existing.revoked_at is not None:
            # Reuse of an already-rotated/revoked token: treat as compromise
            # and kill every token descended from this login. Commit explicitly
            # — the request will raise past this point, and get_db_session
            # rolls back on any exception, which would otherwise undo the
            # revocation we're relying on for security here.
            await self.refresh_tokens.revoke_family(existing.family_id, revoked_at=now)
            await self.session.commit()
            raise UnauthorizedError(
                "Refresh token reuse detected. All sessions have been revoked."
            )

        if existing.expires_at <= now:
            raise UnauthorizedError("Refresh token expired.")

        user = await self.users.get_by_id(existing.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Account is no longer active.")

        settings = get_settings()
        raw_refresh = generate_opaque_token()
        refresh_expires_at = now + timedelta(days=settings.refresh_token_ttl_days)

        new_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            family_id=existing.family_id,
            expires_at=refresh_expires_at,
        )
        await self.refresh_tokens.create(new_token)

        existing.revoked_at = now
        existing.replaced_by_id = new_token.id
        await self.session.flush()

        access_token, expires_in = create_access_token(user_id=user.id, role=user.role.value)
        return user, TokenPair(access_token, expires_in, raw_refresh, refresh_expires_at)

    async def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_token(raw_refresh_token)
        existing = await self.refresh_tokens.get_by_hash(token_hash)
        if existing is not None and existing.revoked_at is None:
            existing.revoked_at = datetime.now(UTC)
            await self.session.flush()

    async def _send_verification_email(self, user: User) -> None:
        token = generate_opaque_token()
        await self.redis.set(
            f"{_EMAIL_VERIFY_PREFIX}{hash_token(token)}",
            str(user.id),
            ex=EMAIL_VERIFY_TTL_SECONDS,
        )
        settings = get_settings()
        verify_url = f"{settings.frontend_url}/verify-email?token={token}"
        await send_email(
            to=user.email,
            subject="Verify your VeriHire email",
            html_body=(
                f"<p>Hi {user.full_name},</p>"
                f'<p><a href="{verify_url}">Verify your email</a> to finish setting up '
                "your VeriHire account. This link expires in 24 hours.</p>"
            ),
        )

    async def resend_verification_email(self, user: User) -> None:
        if not user.email_verified:
            await self._send_verification_email(user)

    async def verify_email(self, token: str) -> None:
        key = f"{_EMAIL_VERIFY_PREFIX}{hash_token(token)}"
        user_id_str = await self.redis.get(key)
        if user_id_str is None:
            raise UnauthorizedError("This verification link is invalid or has expired.")

        await self.redis.delete(key)
        user = await self.users.get_by_id(uuid.UUID(user_id_str))
        if user is not None:
            user.email_verified_at = datetime.now(UTC)
            await self.session.flush()

    async def request_password_reset(self, email: str) -> None:
        user = await self.users.get_by_email(email.lower())
        if user is None:
            return  # Do not reveal whether an account exists.

        token = generate_opaque_token()
        await self.redis.set(
            f"{_PASSWORD_RESET_PREFIX}{hash_token(token)}",
            str(user.id),
            ex=PASSWORD_RESET_TTL_SECONDS,
        )
        settings = get_settings()
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        await send_email(
            to=user.email,
            subject="Reset your VeriHire password",
            html_body=(
                f"<p>Hi {user.full_name},</p>"
                f'<p><a href="{reset_url}">Reset your password</a>. '
                "This link expires in 1 hour and can only be used once.</p>"
            ),
        )

    async def reset_password(self, *, token: str, new_password: str) -> None:
        key = f"{_PASSWORD_RESET_PREFIX}{hash_token(token)}"
        user_id_str = await self.redis.get(key)
        if user_id_str is None:
            raise UnauthorizedError("This reset link is invalid or has expired.")

        await self.redis.delete(key)
        user = await self.users.get_by_id(uuid.UUID(user_id_str))
        if user is None:
            raise UnauthorizedError("This reset link is invalid or has expired.")

        user.password_hash = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.session.flush()

        # A password reset invalidates every existing session.
        family_ids = await self.refresh_tokens.list_family_ids_for_user(user.id)
        now = datetime.now(UTC)
        for family_id in family_ids:
            await self.refresh_tokens.revoke_family(family_id, revoked_at=now)
        await self.session.flush()

    async def start_google_oauth(self, *, redirect_uri: str) -> str:
        """Returns the Google authorization URL for an Authorization Code + PKCE flow."""
        settings = get_settings()
        if not settings.google_oauth_client_id:
            raise NotConfiguredError("Google sign-in is not configured on this deployment.")

        state = generate_opaque_token()
        code_verifier, code_challenge = generate_pkce_pair()
        await self.redis.set(
            f"{_GOOGLE_OAUTH_STATE_PREFIX}{state}",
            f"{code_verifier}|{redirect_uri}",
            ex=GOOGLE_OAUTH_STATE_TTL_SECONDS,
        )
        return build_authorization_url(
            state=state, code_challenge=code_challenge, redirect_uri=redirect_uri
        )

    async def complete_google_oauth(self, *, code: str, state: str) -> tuple[User, TokenPair]:
        key = f"{_GOOGLE_OAUTH_STATE_PREFIX}{state}"
        stored = await self.redis.get(key)
        if stored is None:
            raise UnauthorizedError("This sign-in link is invalid or has expired.")
        await self.redis.delete(key)

        code_verifier, redirect_uri = stored.split("|", 1)

        try:
            userinfo = await exchange_code_for_userinfo(
                code=code, code_verifier=code_verifier, redirect_uri=redirect_uri
            )
        except GoogleOAuthError as exc:
            raise UnauthorizedError(f"Google sign-in failed: {exc}") from exc

        google_sub = userinfo["sub"]
        email = userinfo["email"].lower()
        full_name = userinfo.get("name") or email

        user = await self.users.get_by_google_sub(google_sub)
        if user is None:
            user = await self.users.get_by_email(email)

        if user is None:
            user = User(
                email=email,
                password_hash=None,
                full_name=full_name,
                role=UserRole.SEEKER,
                oauth_google_sub=google_sub,
                email_verified_at=datetime.now(UTC),
            )
            await self.users.create(user)
        elif user.oauth_google_sub is None:
            user.oauth_google_sub = google_sub
            if user.email_verified_at is None:
                user.email_verified_at = datetime.now(UTC)
            await self.session.flush()

        tokens = await self.issue_token_pair(user)
        return user, tokens
