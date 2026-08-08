import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ReportStatus, SubjectType
from app.core.errors import ConflictError, NotFoundError
from app.core.pagination import Page, decode_cursor, paginate_rows
from app.modules.reports.models import Report
from app.modules.reports.repository import ReportRepository
from app.modules.reports.schemas import ReportCreate, ReportRead

DUPLICATE_WINDOW_HOURS = 24
MAX_PAGE_SIZE = 100


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReportRepository(session)

    async def get(self, report_id: uuid.UUID) -> Report:
        report = await self.repo.get_by_id(report_id)
        if report is None:
            raise NotFoundError("Report not found.")
        return report

    async def list_pending(self, *, cursor: str | None, limit: int) -> Page[ReportRead]:
        limit = min(max(limit, 1), MAX_PAGE_SIZE)
        cursor_id = decode_cursor(cursor) if cursor else None
        rows = await self.repo.list_pending(cursor_id=cursor_id, limit=limit)
        page = paginate_rows(rows, limit, lambda r: r.id)
        return Page[ReportRead](
            data=[ReportRead.model_validate(r) for r in page.data],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )

    async def create(
        self,
        payload: ReportCreate,
        *,
        reporter_user_id: uuid.UUID,
        idempotency_key: str | None,
    ) -> Report:
        if idempotency_key:
            existing = await self.repo.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing

        duplicate = await self._find_recent_duplicate(
            payload.subject_type, payload.subject_id, reporter_user_id
        )
        if duplicate is not None:
            raise ConflictError(
                "You've already reported this subject recently. "
                "It's already in the moderation queue."
            )

        report = Report(
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            reporter_user_id=reporter_user_id,
            category=payload.category,
            description=payload.description,
            status=ReportStatus.PENDING,
            idempotency_key=idempotency_key,
        )
        return await self.repo.create(report)

    async def confirm(self, report_id: uuid.UUID, *, moderator_id: uuid.UUID) -> Report:
        report = await self.get(report_id)
        report.status = ReportStatus.CONFIRMED
        report.confirmed_at = datetime.now(UTC)
        report.confirmed_by_user_id = moderator_id
        await self.session.flush()
        return report

    async def reject(self, report_id: uuid.UUID, *, reason: str) -> Report:
        report = await self.get(report_id)
        report.status = ReportStatus.REJECTED
        report.rejection_reason = reason
        await self.session.flush()
        return report

    async def _find_recent_duplicate(
        self, subject_type: SubjectType, subject_id: uuid.UUID, reporter_user_id: uuid.UUID
    ) -> Report | None:
        window_start = datetime.now(UTC) - timedelta(hours=DUPLICATE_WINDOW_HOURS)
        result = await self.session.execute(
            select(Report).where(
                Report.subject_type == subject_type,
                Report.subject_id == subject_id,
                Report.reporter_user_id == reporter_user_id,
                Report.created_at >= window_start,
                Report.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
