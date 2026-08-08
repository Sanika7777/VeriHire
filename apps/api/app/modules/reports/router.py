import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.core.deps import CurrentUser, DbSession
from app.core.pagination import Page
from app.core.rate_limit import RateLimiter
from app.modules.reports.schemas import ReportCreate, ReportRead
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

_report_rate_limit = RateLimiter(times=5, seconds=60 * 60, scope="reports")


def get_report_service(session: DbSession) -> ReportService:
    return ReportService(session)


ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]


@router.get("", response_model=Page[ReportRead])
async def list_pending_reports(
    service: ReportServiceDep,
    cursor: str | None = None,
    limit: int = 20,
) -> Page[ReportRead]:
    return await service.list_pending(cursor=cursor, limit=limit)


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(report_id: uuid.UUID, service: ReportServiceDep) -> ReportRead:
    report = await service.get(report_id)
    return ReportRead.model_validate(report)


@router.post(
    "",
    response_model=ReportRead,
    status_code=201,
    dependencies=[Depends(_report_rate_limit)],
)
async def create_report(
    body: ReportCreate,
    service: ReportServiceDep,
    user: CurrentUser,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ReportRead:
    report = await service.create(
        body, reporter_user_id=user.id, idempotency_key=idempotency_key
    )
    return ReportRead.model_validate(report)
