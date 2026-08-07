import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.enums import UserRole
from app.core.pagination import Page
from app.modules.postings.schemas import JobPostingCreate, JobPostingRead
from app.modules.postings.service import JobPostingService
from app.modules.users.models import User

router = APIRouter(prefix="/postings", tags=["postings"])

RequireStaff = Annotated[User, Depends(require_roles(UserRole.MODERATOR, UserRole.ADMIN))]


def get_posting_service(session: DbSession) -> JobPostingService:
    return JobPostingService(session)


JobPostingServiceDep = Annotated[JobPostingService, Depends(get_posting_service)]


@router.get("", response_model=Page[JobPostingRead])
async def list_postings(
    service: JobPostingServiceDep,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> Page[JobPostingRead]:
    return await service.list(cursor=cursor, limit=limit)


@router.get("/{posting_id}", response_model=JobPostingRead)
async def get_posting(posting_id: uuid.UUID, service: JobPostingServiceDep) -> JobPostingRead:
    posting = await service.get(posting_id)
    return JobPostingRead.model_validate(posting)


@router.post("", response_model=JobPostingRead, status_code=201)
async def create_posting(
    body: JobPostingCreate,
    service: JobPostingServiceDep,
    _user: CurrentUser,
) -> JobPostingRead:
    posting = await service.create(body)
    return JobPostingRead.model_validate(posting)


@router.delete("/{posting_id}", status_code=204)
async def delete_posting(
    posting_id: uuid.UUID,
    service: JobPostingServiceDep,
    _staff: RequireStaff,
) -> None:
    await service.soft_delete(posting_id)
