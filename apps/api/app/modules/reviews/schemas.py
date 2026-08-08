import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import SubjectType


class ReviewCreate(BaseModel):
    subject_type: SubjectType
    subject_id: uuid.UUID
    rating_communication: int = Field(ge=1, le=5)
    rating_process_transparency: int = Field(ge=1, le=5)
    rating_offer_accuracy: int = Field(ge=1, le=5)
    rating_professionalism: int = Field(ge=1, le=5)
    body: str | None = Field(default=None, max_length=5000)
    verified_interaction: bool = False


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_type: SubjectType
    subject_id: uuid.UUID
    rating_communication: int
    rating_process_transparency: int
    rating_offer_accuracy: int
    rating_professionalism: int
    body: str | None
    verified_interaction: bool
    helpful_count: int
    unhelpful_count: int
    created_at: datetime


class ReviewVoteCreate(BaseModel):
    is_helpful: bool
