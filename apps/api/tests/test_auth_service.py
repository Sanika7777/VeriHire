from __future__ import annotations

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AccountLockedError, ConflictError, UnauthorizedError
from app.modules.auth.service import LOCKOUT_THRESHOLD, AuthService

EMAIL = "ananya.iyer@example.com"
PASSWORD = "CorrectHorseBattery9"


async def _register(service: AuthService) -> None:
    await service.register(email=EMAIL, password=PASSWORD, full_name="Ananya Iyer")


async def test_register_then_authenticate_succeeds(
    db_session: AsyncSession, redis_client: Redis[str]
) -> None:
    service = AuthService(db_session, redis_client)
    await _register(service)

    user = await service.authenticate(email=EMAIL, password=PASSWORD)
    assert user.email == EMAIL
    assert user.role.value == "seeker"


async def test_register_duplicate_email_raises_conflict(
    db_session: AsyncSession, redis_client: Redis[str]
) -> None:
    service = AuthService(db_session, redis_client)
    await _register(service)

    with pytest.raises(ConflictError):
        await _register(service)


async def test_wrong_password_raises_unauthorized(
    db_session: AsyncSession, redis_client: Redis[str]
) -> None:
    service = AuthService(db_session, redis_client)
    await _register(service)

    with pytest.raises(UnauthorizedError):
        await service.authenticate(email=EMAIL, password="totally-wrong-password")


async def test_account_locks_after_repeated_failures(
    db_session: AsyncSession, redis_client: Redis[str]
) -> None:
    service = AuthService(db_session, redis_client)
    await _register(service)

    for _ in range(LOCKOUT_THRESHOLD - 1):
        with pytest.raises(UnauthorizedError):
            await service.authenticate(email=EMAIL, password="wrong")

    # The Nth failure crosses the threshold and locks the account.
    with pytest.raises(UnauthorizedError):
        await service.authenticate(email=EMAIL, password="wrong")

    # Even the correct password is rejected while locked.
    with pytest.raises(AccountLockedError):
        await service.authenticate(email=EMAIL, password=PASSWORD)


async def test_refresh_token_rotation_reuse_revokes_whole_family(
    db_session: AsyncSession, redis_client: Redis[str]
) -> None:
    service = AuthService(db_session, redis_client)
    await _register(service)
    user = await service.authenticate(email=EMAIL, password=PASSWORD)

    original = await service.issue_token_pair(user)

    # A normal rotation succeeds and yields a fresh raw token.
    _, rotated = await service.rotate_refresh_token(original.refresh_token)
    assert rotated.refresh_token != original.refresh_token

    # Replaying the now-revoked original token is reuse: it must fail...
    with pytest.raises(UnauthorizedError, match="reuse detected"):
        await service.rotate_refresh_token(original.refresh_token)

    # ...and must also have revoked the token that replaced it.
    with pytest.raises(UnauthorizedError):
        await service.rotate_refresh_token(rotated.refresh_token)


async def test_refresh_token_rotation_rejects_unknown_token(
    db_session: AsyncSession, redis_client: Redis[str]
) -> None:
    service = AuthService(db_session, redis_client)
    with pytest.raises(UnauthorizedError):
        await service.rotate_refresh_token("not-a-real-token")
