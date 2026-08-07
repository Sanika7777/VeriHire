import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.redis import get_redis
from app.core.security import InvalidAccessTokenError, decode_access_token
from app.db.session import get_db_session
from app.modules.auth.service import AuthService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_auth_service(session: DbSession) -> AuthService:
    # get_redis() is called directly (not via Depends) because redis-py's
    # Redis class cannot be subscripted at runtime — wrapping it in Depends
    # makes FastAPI call typing.get_type_hints() on the dependency callable,
    # which evaluates `Redis[str]` and raises TypeError.
    return AuthService(session, get_redis())


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header.")

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except InvalidAccessTokenError as exc:
        raise UnauthorizedError("Invalid or expired access token.") from exc

    user = await UserRepository(session).get_by_id(uuid.UUID(payload["sub"]))
    if user is None or not user.is_active or user.deleted_at is not None:
        raise UnauthorizedError("Account no longer exists.")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    async def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to perform this action.")
        return user

    return dependency
