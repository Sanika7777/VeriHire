from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.all_models  # noqa: F401

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://verihire@127.0.0.1:5433/verihire"
)
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6380/0")


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """A session bound to a connection-level transaction that is always
    rolled back, so every test starts clean regardless of what it does.

    Service code sometimes calls `session.commit()` deliberately (e.g. to
    persist a security-critical write before raising an error — see
    AuthService.rotate_refresh_token). `join_transaction_mode="create_savepoint"`
    makes those inner commits release a SAVEPOINT instead of the outer
    transaction, so the final rollback here still discards everything.
    """
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.connect() as conn:
        await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with session_factory() as session:
            yield session
        await conn.rollback()
    await engine.dispose()


@pytest.fixture
async def redis_client() -> AsyncGenerator[Redis[str]]:
    client: Redis[str] = Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    yield client
    await client.flushdb()
    await client.aclose()
