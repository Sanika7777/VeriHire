import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.arq_pool import get_arq_pool
from app.core.deps import DbSession, require_roles
from app.core.enums import ReportStatus, TrustBand, UserRole
from app.core.errors import ConflictError
from app.core.pagination import Page
from app.modules.admin.repository import AuditLogRepository
from app.modules.admin.schemas import (
    DashboardSummary,
    MergeEntitiesRequest,
    ScoringConfigPreviewImpact,
    ScoringConfigRead,
    ScoringConfigUpdate,
)
from app.modules.companies.schemas import CompanyRead
from app.modules.companies.service import CompanyService
from app.modules.recruiters.schemas import RecruiterRead
from app.modules.recruiters.service import RecruiterService
from app.modules.reports.models import Report
from app.modules.reports.schemas import ReportModerationDecision, ReportRead
from app.modules.reports.service import ReportService
from app.modules.users.models import Notification, User
from app.modules.verification.models import Verification
from app.modules.verification.service import VerificationService

router = APIRouter(prefix="/admin", tags=["admin"])

RequireStaff = Annotated[User, Depends(require_roles(UserRole.MODERATOR, UserRole.ADMIN))]
RequireAdmin = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def get_report_service(session: DbSession) -> ReportService:
    return ReportService(session)


def get_verification_service(session: DbSession) -> VerificationService:
    return VerificationService(session)


def get_company_service(session: DbSession) -> CompanyService:
    return CompanyService(session)


def get_recruiter_service(session: DbSession) -> RecruiterService:
    return RecruiterService(session)


def get_audit_log_repository(session: DbSession) -> AuditLogRepository:
    return AuditLogRepository(session)


ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
VerificationServiceDep = Annotated[VerificationService, Depends(get_verification_service)]
CompanyServiceDep = Annotated[CompanyService, Depends(get_company_service)]
RecruiterServiceDep = Annotated[RecruiterService, Depends(get_recruiter_service)]
AuditLogRepositoryDep = Annotated[AuditLogRepository, Depends(get_audit_log_repository)]


async def _notify_reporter(
    session: DbSession, report: Report, *, title: str, body: str
) -> None:
    if report.reporter_user_id is None:
        return
    session.add(
        Notification(
            user_id=report.reporter_user_id,
            type="report_status_changed",
            title=title,
            body=body,
        )
    )
    await session.flush()


@router.get("/ping")
async def ping(user: RequireStaff) -> dict[str, str]:
    return {"status": "ok", "role": user.role.value}


@router.get("/reports", response_model=Page[ReportRead])
async def list_pending_reports(
    _staff: RequireStaff,
    service: ReportServiceDep,
    cursor: str | None = None,
    limit: int = 20,
) -> Page[ReportRead]:
    return await service.list_pending(cursor=cursor, limit=limit)


@router.post("/reports/{report_id}/confirm", response_model=ReportRead)
async def confirm_report(
    report_id: uuid.UUID,
    body: ReportModerationDecision,
    staff: RequireStaff,
    service: ReportServiceDep,
    verification_service: VerificationServiceDep,
    audit_logs: AuditLogRepositoryDep,
    session: DbSession,
) -> ReportRead:
    """Confirming a fraud report hard-caps the subject's score at 25
    (CLAUDE.md §5) — enforced by the aggregator once it sees the confirmed
    report, triggered here by enqueuing a fresh verification."""
    before = await service.get(report_id)
    before_status = before.status.value

    report = await service.confirm(report_id, moderator_id=staff.id)

    await audit_logs.record(
        actor_user_id=staff.id,
        action="report.confirm",
        entity_type="report",
        entity_id=report.id,
        before={"status": before_status},
        after={"status": report.status.value},
        reason=body.reason,
    )
    await _notify_reporter(
        session,
        report,
        title="Your report was confirmed",
        body="Thanks for the report — our moderation team confirmed it and the "
        "subject's Trust Score has been updated.",
    )

    verification = await verification_service.create_pending(
        report.subject_type, report.subject_id, staff.id
    )
    pool = await get_arq_pool()
    await pool.enqueue_job("compute_verification", str(verification.id))

    return ReportRead.model_validate(report)


@router.post("/reports/{report_id}/reject", response_model=ReportRead)
async def reject_report(
    report_id: uuid.UUID,
    body: ReportModerationDecision,
    staff: RequireStaff,
    service: ReportServiceDep,
    audit_logs: AuditLogRepositoryDep,
    session: DbSession,
) -> ReportRead:
    before = await service.get(report_id)
    before_status = before.status.value

    report = await service.reject(report_id, reason=body.reason)

    await audit_logs.record(
        actor_user_id=staff.id,
        action="report.reject",
        entity_type="report",
        entity_id=report.id,
        before={"status": before_status},
        after={"status": report.status.value},
        reason=body.reason,
    )
    await _notify_reporter(
        session,
        report,
        title="Your report was reviewed",
        body=f"Our moderation team reviewed your report and did not confirm it. Reason: {body.reason}",
    )

    return ReportRead.model_validate(report)


@router.get("/dashboard", response_model=DashboardSummary)
async def dashboard(_staff: RequireStaff, session: DbSession) -> DashboardSummary:
    pending_count = await session.scalar(
        select(func.count()).select_from(Report).where(Report.status == ReportStatus.PENDING)
    )
    confirmed_count = await session.scalar(
        select(func.count()).select_from(Report).where(Report.status == ReportStatus.CONFIRMED)
    )
    rejected_count = await session.scalar(
        select(func.count()).select_from(Report).where(Report.status == ReportStatus.REJECTED)
    )

    week_ago = datetime.now(UTC) - timedelta(days=7)
    verifications_7d = await session.scalar(
        select(func.count())
        .select_from(Verification)
        .where(Verification.computed_at >= week_ago)
    )

    band_rows = (
        await session.execute(select(Verification.band, func.count()).group_by(Verification.band))
    ).all()
    band_distribution = {row[0].value: row[1] for row in band_rows}
    for band in TrustBand:
        band_distribution.setdefault(band.value, 0)

    top_reported_rows = (
        await session.execute(
            select(Report.subject_type, Report.subject_id, func.count().label("n"))
            .where(Report.deleted_at.is_(None))
            .group_by(Report.subject_type, Report.subject_id)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()
    top_reported = [
        {"subject_type": row[0].value, "subject_id": str(row[1]), "report_count": row[2]}
        for row in top_reported_rows
    ]

    return DashboardSummary(
        pending_reports=pending_count or 0,
        confirmed_reports=confirmed_count or 0,
        rejected_reports=rejected_count or 0,
        verifications_last_7_days=verifications_7d or 0,
        band_distribution=band_distribution,
        top_reported_subjects=top_reported,
    )


@router.get("/scoring-config", response_model=ScoringConfigRead)
async def get_scoring_config(
    _staff: RequireStaff, verification_service: VerificationServiceDep
) -> ScoringConfigRead:
    config = await verification_service.get_active_scoring_config()
    return ScoringConfigRead.model_validate(config, from_attributes=True)


@router.post("/scoring-config/preview", response_model=ScoringConfigPreviewImpact)
async def preview_scoring_config(
    body: ScoringConfigUpdate,
    _staff: RequireStaff,
    verification_service: VerificationServiceDep,
) -> ScoringConfigPreviewImpact:
    impact = await verification_service.preview_weight_change(body.weights)
    return ScoringConfigPreviewImpact(**impact)


@router.put("/scoring-config", response_model=ScoringConfigRead)
async def publish_scoring_config(
    body: ScoringConfigUpdate,
    admin: RequireAdmin,
    verification_service: VerificationServiceDep,
    audit_logs: AuditLogRepositoryDep,
) -> ScoringConfigRead:
    weight_sum = round(sum(body.weights.values()), 4)
    if weight_sum != 1.0:
        raise ConflictError(f"Weights must sum to 1.0 (got {weight_sum}).")

    config = await verification_service.publish_scoring_config(
        body.weights, body.thresholds, created_by=admin.id
    )
    await audit_logs.record(
        actor_user_id=admin.id,
        action="scoring_config.publish",
        entity_type="scoring_config",
        entity_id=config.id,
        before=None,
        after={"version": config.version, "weights": config.weights},
        reason="Weight configuration published from admin console.",
    )
    return ScoringConfigRead.model_validate(config, from_attributes=True)


@router.post("/companies/merge", response_model=CompanyRead)
async def merge_companies(
    body: MergeEntitiesRequest,
    staff: RequireStaff,
    service: CompanyServiceDep,
    audit_logs: AuditLogRepositoryDep,
) -> CompanyRead:
    target = await service.merge(body.source_id, body.target_id)
    await audit_logs.record(
        actor_user_id=staff.id,
        action="company.merge",
        entity_type="company",
        entity_id=body.source_id,
        before={"merged_into": None},
        after={"merged_into": str(body.target_id)},
        reason=body.reason,
    )
    return CompanyRead.model_validate(target)


@router.post("/recruiters/merge", response_model=RecruiterRead)
async def merge_recruiters(
    body: MergeEntitiesRequest,
    staff: RequireStaff,
    service: RecruiterServiceDep,
    audit_logs: AuditLogRepositoryDep,
) -> RecruiterRead:
    target = await service.merge(body.source_id, body.target_id)
    await audit_logs.record(
        actor_user_id=staff.id,
        action="recruiter.merge",
        entity_type="recruiter",
        entity_id=body.source_id,
        before={"merged_into": None},
        after={"merged_into": str(body.target_id)},
        reason=body.reason,
    )
    return RecruiterRead.model_validate(target)
