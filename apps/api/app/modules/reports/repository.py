import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ReportStatus
from app.modules.reports.models import Report


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, report_id: uuid.UUID) -> Report | None:
        result = await self.session.execute(
            select(Report).where(Report.id == report_id, Report.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Report | None:
        result = await self.session.execute(
            select(Report).where(Report.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def list_pending(self, *, cursor_id: uuid.UUID | None, limit: int) -> list[Report]:
        query = (
            select(Report)
            .where(Report.status == ReportStatus.PENDING, Report.deleted_at.is_(None))
            .order_by(Report.id)
        )
        if cursor_id is not None:
            query = query.where(Report.id > cursor_id)
        result = await self.session.execute(query.limit(limit + 1))
        return list(result.scalars().all())

    async def create(self, report: Report) -> Report:
        self.session.add(report)
        await self.session.flush()
        return report
