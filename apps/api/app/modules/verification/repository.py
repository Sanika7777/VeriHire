import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubjectType, VerificationStatus
from app.modules.verification.models import ScoringConfig, Verification, VerificationSignal


class VerificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, verification_id: uuid.UUID) -> Verification | None:
        return await self.session.get(Verification, verification_id)

    async def get_latest(
        self, subject_type: SubjectType, subject_id: uuid.UUID
    ) -> Verification | None:
        result = await self.session.execute(
            select(Verification)
            .where(
                Verification.subject_type == subject_type,
                Verification.subject_id == subject_id,
            )
            .order_by(Verification.computed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(
        self, subject_type: SubjectType, subject_id: uuid.UUID, limit: int = 20
    ) -> list[Verification]:
        result = await self.session.execute(
            select(Verification)
            .where(
                Verification.subject_type == subject_type,
                Verification.subject_id == subject_id,
            )
            .order_by(Verification.computed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, verification: Verification) -> Verification:
        self.session.add(verification)
        await self.session.flush()
        return verification

    async def add_signal_rows(self, rows: list[VerificationSignal]) -> None:
        self.session.add_all(rows)
        await self.session.flush()

    async def get_active_scoring_config(self) -> ScoringConfig | None:
        result = await self.session.execute(
            select(ScoringConfig).where(ScoringConfig.is_active.is_(True)).limit(1)
        )
        return result.scalar_one_or_none()

    async def create_scoring_config(self, config: ScoringConfig) -> ScoringConfig:
        self.session.add(config)
        await self.session.flush()
        return config

    async def next_scoring_config_version(self) -> int:
        # `version` isn't the primary key, so Postgres has no sequence for
        # it — compute the next value explicitly rather than relying on
        # SQLAlchemy's autoincrement (which only applies to single-column
        # integer primary keys).
        result = await self.session.execute(select(func.max(ScoringConfig.version)))
        current_max = result.scalar_one_or_none()
        return (current_max or 0) + 1

    async def deactivate_all_scoring_configs(self) -> None:
        await self.session.execute(update(ScoringConfig).values(is_active=False))

    async def sample_recent_done_verifications(self, limit: int) -> list[Verification]:
        result = await self.session.execute(
            select(Verification)
            .where(Verification.status == VerificationStatus.DONE)
            .order_by(Verification.computed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
