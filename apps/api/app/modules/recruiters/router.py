import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.enums import UserRole
from app.core.pagination import Page
from app.modules.recruiters.schemas import RecruiterCreate, RecruiterRead, RecruiterUpdate
from app.modules.recruiters.service import RecruiterService
from app.modules.users.models import User

router = APIRouter(prefix="/recruiters", tags=["recruiters"])

RequireStaff = Annotated[User, Depends(require_roles(UserRole.MODERATOR, UserRole.ADMIN))]


def get_recruiter_service(session: DbSession) -> RecruiterService:
    return RecruiterService(session)


RecruiterServiceDep = Annotated[RecruiterService, Depends(get_recruiter_service)]


@router.get("", response_model=Page[RecruiterRead])
async def list_recruiters(
    service: RecruiterServiceDep,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> Page[RecruiterRead]:
    return await service.list(cursor=cursor, limit=limit)


@router.get("/{recruiter_id}", response_model=RecruiterRead)
async def get_recruiter(recruiter_id: uuid.UUID, service: RecruiterServiceDep) -> RecruiterRead:
    recruiter = await service.get(recruiter_id)
    return RecruiterRead.model_validate(recruiter)


@router.post("", response_model=RecruiterRead, status_code=201)
async def create_recruiter(
    body: RecruiterCreate,
    service: RecruiterServiceDep,
    _user: CurrentUser,
) -> RecruiterRead:
    recruiter = await service.create(body)
    return RecruiterRead.model_validate(recruiter)


@router.patch("/{recruiter_id}", response_model=RecruiterRead)
async def update_recruiter(
    recruiter_id: uuid.UUID,
    body: RecruiterUpdate,
    service: RecruiterServiceDep,
    _staff: RequireStaff,
) -> RecruiterRead:
    recruiter = await service.update(recruiter_id, body)
    return RecruiterRead.model_validate(recruiter)


@router.delete("/{recruiter_id}", status_code=204)
async def delete_recruiter(
    recruiter_id: uuid.UUID,
    service: RecruiterServiceDep,
    _staff: RequireStaff,
) -> None:
    await service.soft_delete(recruiter_id)
