from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.core.security import create_access_token, hash_password
from app.db.session import get_db_session
from app.main import app
from app.modules.users.models import User


async def _create_user(session: AsyncSession, *, role: UserRole, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("irrelevant-for-this-test"),
        full_name="Test User",
        role=role,
    )
    session.add(user)
    await session.flush()
    return user


def _bearer(user: User) -> dict[str, str]:
    token, _ = create_access_token(user_id=user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    # The running app resolves its own DB session per-request via
    # get_db_session; override it so requests see the same transaction (and
    # therefore the same not-yet-committed test fixtures) as this test.
    async def _override() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        (UserRole.SEEKER, 403),
        (UserRole.EMPLOYER, 403),
        (UserRole.MODERATOR, 200),
        (UserRole.ADMIN, 200),
    ],
)
async def test_staff_route_boundary_by_role(
    db_session: AsyncSession,
    redis_client: Redis[str],
    client: AsyncClient,
    role: UserRole,
    expected_status: int,
) -> None:
    user = await _create_user(db_session, role=role, email=f"{role.value}@example.com")

    response = await client.get("/api/v1/admin/ping", headers=_bearer(user))

    assert response.status_code == expected_status


async def test_staff_route_rejects_anonymous_request(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/ping")
    assert response.status_code == 401


async def test_staff_route_rejects_malformed_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/admin/ping", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401
