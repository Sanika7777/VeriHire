from __future__ import annotations

from typing import Any

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotConfiguredError
from app.modules.auth import service as auth_service_module
from app.modules.auth.service import AuthService
from app.modules.users.models import User

STATE_KEY = "auth:google-oauth-state:test-state"


async def test_start_google_oauth_raises_when_not_configured(
    db_session: AsyncSession, redis_client: Redis[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Explicitly clear rather than relying on the ambient environment/.env
    # having no Google OAuth credentials — a developer with real local
    # credentials configured would otherwise get a spurious failure here.
    settings = get_settings()
    monkeypatch.setattr(settings, "google_oauth_client_id", None)
    monkeypatch.setattr(settings, "google_oauth_client_secret", None)

    service = AuthService(db_session, redis_client)
    with pytest.raises(NotConfiguredError):
        await service.start_google_oauth(redirect_uri="http://localhost:3000/callback")


async def test_complete_google_oauth_creates_new_user(
    db_session: AsyncSession,
    redis_client: Redis[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AuthService(db_session, redis_client)
    await redis_client.set(STATE_KEY, "verifier123|http://localhost:3000/callback")

    async def fake_exchange(*, code: str, code_verifier: str, redirect_uri: str) -> dict[str, Any]:
        assert code_verifier == "verifier123"
        return {
            "sub": "google-sub-001",
            "email": "New.User@example.com",
            "email_verified": True,
            "name": "New User",
        }

    monkeypatch.setattr(auth_service_module, "exchange_code_for_userinfo", fake_exchange)

    user, tokens = await service.complete_google_oauth(code="anycode", state="test-state")

    assert user.email == "new.user@example.com"
    assert user.oauth_google_sub == "google-sub-001"
    assert user.email_verified is True
    assert user.password_hash is None
    assert tokens.access_token

    # State is single-use.
    assert await redis_client.get(STATE_KEY) is None


async def test_complete_google_oauth_links_existing_email(
    db_session: AsyncSession,
    redis_client: Redis[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = User(
        email="linked.user@example.com",
        password_hash="irrelevant",
        full_name="Linked User",
    )
    db_session.add(existing)
    await db_session.flush()

    service = AuthService(db_session, redis_client)
    await redis_client.set(STATE_KEY, "verifier456|http://localhost:3000/callback")

    async def fake_exchange(*, code: str, code_verifier: str, redirect_uri: str) -> dict[str, Any]:
        return {
            "sub": "google-sub-002",
            "email": "linked.user@example.com",
            "email_verified": True,
            "name": "Linked User",
        }

    monkeypatch.setattr(auth_service_module, "exchange_code_for_userinfo", fake_exchange)

    user, _ = await service.complete_google_oauth(code="anycode", state="test-state")

    assert user.id == existing.id
    assert user.oauth_google_sub == "google-sub-002"


async def test_complete_google_oauth_rejects_unknown_state(
    db_session: AsyncSession, redis_client: Redis[str]
) -> None:
    service = AuthService(db_session, redis_client)
    with pytest.raises(Exception, match="invalid or has expired"):
        await service.complete_google_oauth(code="anycode", state="never-issued")
