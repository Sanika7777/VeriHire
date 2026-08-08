import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.arq_pool import get_arq_pool
from app.core.deps import CurrentUser, DbSession
from app.core.enums import SubjectType, VerificationStatus
from app.db.session import async_session_factory
from app.modules.verification.models import Verification
from app.modules.verification.schemas import (
    VerificationCreate,
    VerificationCreateResponse,
    VerificationRead,
)
from app.modules.verification.service import VerificationService

router = APIRouter(prefix="/verifications", tags=["verifications"])


def get_verification_service(session: DbSession) -> VerificationService:
    return VerificationService(session)


VerificationServiceDep = Annotated[VerificationService, Depends(get_verification_service)]

TERMINAL_STATUSES = {VerificationStatus.DONE, VerificationStatus.FAILED}


@router.post("", response_model=VerificationCreateResponse, status_code=202)
async def request_verification(
    body: VerificationCreate,
    service: VerificationServiceDep,
    user: CurrentUser,
) -> VerificationCreateResponse:
    verification = await service.create_pending(body.subject_type, body.subject_id, user.id)
    pool = await get_arq_pool()
    await pool.enqueue_job("compute_verification", str(verification.id))
    return VerificationCreateResponse(verification_id=verification.id, status=verification.status)


@router.get("/latest", response_model=VerificationRead | None)
async def get_latest(
    service: VerificationServiceDep,
    subject_type: SubjectType,
    subject_id: uuid.UUID,
) -> VerificationRead | None:
    verification = await service.get_latest(subject_type, subject_id)
    return VerificationRead.model_validate(verification) if verification else None


@router.get("/history", response_model=list[VerificationRead])
async def get_history(
    service: VerificationServiceDep,
    subject_type: SubjectType,
    subject_id: uuid.UUID,
) -> list[VerificationRead]:
    history = await service.get_history(subject_type, subject_id)
    return [VerificationRead.model_validate(v) for v in history]


@router.get("/{verification_id}", response_model=VerificationRead)
async def get_verification(
    verification_id: uuid.UUID, service: VerificationServiceDep
) -> VerificationRead:
    verification = await service.get_by_id(verification_id)
    return VerificationRead.model_validate(verification)


async def _poll_status_events(verification_id: uuid.UUID) -> AsyncGenerator[str]:
    """Independent DB session — this generator outlives the request's
    injected session, which closes as soon as the route handler returns the
    StreamingResponse object rather than when the stream finishes."""
    last_status: VerificationStatus | None = None
    max_iterations = 200  # ~60s at 300ms/poll — long enough for a cold run

    for _ in range(max_iterations):
        async with async_session_factory() as session:
            result = await session.execute(
                select(Verification).where(Verification.id == verification_id)
            )
            verification = result.scalar_one_or_none()

        if verification is None:
            yield f"event: error\ndata: {json.dumps({'detail': 'not found'})}\n\n"
            return

        if verification.status != last_status:
            last_status = verification.status
            payload = {
                "status": verification.status.value,
                "score": verification.score,
                "band": verification.band.value,
            }
            yield f"event: stage\ndata: {json.dumps(payload)}\n\n"

        if verification.status in TERMINAL_STATUSES:
            return

        await asyncio.sleep(0.3)

    yield f"event: error\ndata: {json.dumps({'detail': 'timed out waiting for verification'})}\n\n"


@router.get("/{verification_id}/stream")
async def stream_verification(verification_id: uuid.UUID) -> StreamingResponse:
    return StreamingResponse(
        _poll_status_events(verification_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
