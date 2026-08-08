from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.deps import DbSession, require_roles
from app.core.enums import ReportStatus, UserRole
from app.modules.reports.models import Report
from app.modules.users.models import User
from app.modules.verification.models import Verification

router = APIRouter(tags=["observability"])

RequireStaff = Annotated[User, Depends(require_roles(UserRole.MODERATOR, UserRole.ADMIN))]


@router.get("/metrics")
async def metrics(session: DbSession, _staff: RequireStaff) -> dict[str, int]:
    """Minimal operational counters (CLAUDE.md §10). Not Prometheus exposition
    format — a real deployment would swap this for prometheus-fastapi-instrumentator —
    but every number here is live, not a placeholder."""
    users_count = await session.scalar(select(func.count()).select_from(User))
    verifications_count = await session.scalar(select(func.count()).select_from(Verification))
    pending_reports = await session.scalar(
        select(func.count()).select_from(Report).where(Report.status == ReportStatus.PENDING)
    )

    return {
        "users_total": users_count or 0,
        "verifications_total": verifications_count or 0,
        "reports_pending": pending_reports or 0,
    }
