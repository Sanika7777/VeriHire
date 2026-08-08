import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.enums import SubjectType, TrustBand, VerificationStatus


class VerificationCreate(BaseModel):
    subject_type: SubjectType
    subject_id: uuid.UUID


class VerificationCreateResponse(BaseModel):
    verification_id: uuid.UUID
    status: VerificationStatus


class SignalRead(BaseModel):
    sub_score_code: str
    code: str
    severity: str
    title: str
    detail: str
    evidence_url: str | None = None


class VerificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_type: SubjectType
    subject_id: uuid.UUID
    score: int | None
    band: TrustBand
    sub_scores: dict[str, Any]
    signals: list[SignalRead]
    model_version: str | None
    config_version: int | None
    status: VerificationStatus
    error_detail: str | None
    hard_override_reason: str | None
    computed_at: datetime
