import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    pending_reports: int
    confirmed_reports: int
    rejected_reports: int
    verifications_last_7_days: int
    band_distribution: dict[str, int]
    top_reported_subjects: list[dict[str, object]]


class ScoringConfigRead(BaseModel):
    id: uuid.UUID
    version: int
    weights: dict[str, float]
    thresholds: dict[str, object]
    is_active: bool
    created_at: datetime
    published_at: datetime | None


class ScoringConfigUpdate(BaseModel):
    weights: dict[str, float]
    thresholds: dict[str, object] = Field(default_factory=dict)


class ScoringConfigPreviewImpact(BaseModel):
    sample_size: int
    average_score_before: float | None
    average_score_after: float | None
    band_shifts: dict[str, int]


class MergeEntitiesRequest(BaseModel):
    source_id: uuid.UUID
    target_id: uuid.UUID
    reason: str = Field(min_length=5, max_length=2000)
