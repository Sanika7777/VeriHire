from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

# Managed Postgres providers (Neon, Render, etc.) hand out connection
# strings with a libpq-style `?sslmode=require` query param. asyncpg has no
# such kwarg — passing it straight through raises `TypeError: connect() got
# an unexpected keyword argument 'sslmode'` at the first real connection.
# Translate it into the `ssl` connect_arg asyncpg actually understands.
_SSLMODE_TO_ASYNCPG_SSL: dict[str, bool] = {
    "disable": False,
    "allow": True,
    "prefer": True,
    "require": True,
    "verify-ca": True,
    "verify-full": True,
}


def build_database_url_and_connect_args(raw_url: str) -> tuple[str, dict[str, Any]]:
    url = make_url(raw_url)
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    connect_args: dict[str, Any] = {}
    if sslmode is not None:
        connect_args["ssl"] = _SSLMODE_TO_ASYNCPG_SSL.get(str(sslmode), True)
    return url.set(query=query).render_as_string(hide_password=False), connect_args


def create_engine() -> AsyncEngine:
    settings = get_settings()
    database_url, connect_args = build_database_url_and_connect_args(str(settings.database_url))
    return create_async_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.debug,
    )


engine: AsyncEngine = create_engine()

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def ping_database() -> bool:
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
