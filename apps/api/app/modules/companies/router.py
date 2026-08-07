import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.enums import UserRole
from app.core.pagination import Page
from app.modules.companies.schemas import CompanyCreate, CompanyRead, CompanyUpdate
from app.modules.companies.service import CompanyService
from app.modules.users.models import User

router = APIRouter(prefix="/companies", tags=["companies"])

RequireStaff = Annotated[User, Depends(require_roles(UserRole.MODERATOR, UserRole.ADMIN))]


def get_company_service(session: DbSession) -> CompanyService:
    return CompanyService(session)


CompanyServiceDep = Annotated[CompanyService, Depends(get_company_service)]


@router.get("", response_model=Page[CompanyRead])
async def list_companies(
    service: CompanyServiceDep,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> Page[CompanyRead]:
    return await service.list(cursor=cursor, limit=limit)


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(company_id: uuid.UUID, service: CompanyServiceDep) -> CompanyRead:
    company = await service.get(company_id)
    return CompanyRead.model_validate(company)


@router.get("/slug/{slug}", response_model=CompanyRead)
async def get_company_by_slug(slug: str, service: CompanyServiceDep) -> CompanyRead:
    company = await service.get_by_slug(slug)
    return CompanyRead.model_validate(company)


@router.post("", response_model=CompanyRead, status_code=201)
async def create_company(
    body: CompanyCreate,
    service: CompanyServiceDep,
    _user: CurrentUser,
) -> CompanyRead:
    company = await service.create(body)
    return CompanyRead.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyRead)
async def update_company(
    company_id: uuid.UUID,
    body: CompanyUpdate,
    service: CompanyServiceDep,
    _staff: RequireStaff,
) -> CompanyRead:
    company = await service.update(company_id, body)
    return CompanyRead.model_validate(company)


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: uuid.UUID,
    service: CompanyServiceDep,
    _staff: RequireStaff,
) -> None:
    await service.soft_delete(company_id)
