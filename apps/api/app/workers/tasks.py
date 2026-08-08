import uuid

import app.db.all_models  # noqa: F401  (registers every model with Base.metadata)
from app.db.session import async_session_factory
from app.modules.verification.service import VerificationService


async def compute_verification(ctx: dict[str, object], verification_id: str) -> None:  # noqa: ARG001
    async with async_session_factory() as session:
        service = VerificationService(session)
        await service.compute(uuid.UUID(verification_id))
        await session.commit()
