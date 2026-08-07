from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import require_roles
from app.core.enums import UserRole
from app.modules.users.models import User

router = APIRouter(prefix="/admin", tags=["admin"])

RequireStaff = Annotated[User, Depends(require_roles(UserRole.MODERATOR, UserRole.ADMIN))]


@router.get("/ping")
async def ping(user: RequireStaff) -> dict[str, str]:
    """Minimal staff-only route proving the role-guard dependency works.

    The real admin console lands in a later phase; this exists so Phase 2's
    role-guard boundary tests (anon/seeker/moderator/admin) have a route to
    exercise against.
    """
    return {"status": "ok", "role": user.role.value}
