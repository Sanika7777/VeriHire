import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ReportCategory, ReportStatus, SubjectType


class ReportCreate(BaseModel):
    subject_type: SubjectType
    subject_id: uuid.UUID
    category: ReportCategory
    description: str = Field(min_length=10, max_length=5000)


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_type: SubjectType
    subject_id: uuid.UUID
    category: ReportCategory
    status: ReportStatus
    description: str
    rejection_reason: str | None
    created_at: datetime


class ReportModerationDecision(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)
