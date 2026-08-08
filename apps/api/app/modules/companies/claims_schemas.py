import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import ClaimMethod, ClaimStatus


class ClaimStart(BaseModel):
    method: ClaimMethod


class ClaimStartResponse(BaseModel):
    claim_id: uuid.UUID
    method: ClaimMethod
    instructions: str
    verification_token: str


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    method: ClaimMethod
    status: ClaimStatus
    claimed_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
