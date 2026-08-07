import uuid
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.core.enums import SubjectType


class ResolveRequest(BaseModel):
    url: HttpUrl = Field(description="A job posting link, recruiter profile URL, or company domain.")


class ResolveResponse(BaseModel):
    subject_type: SubjectType
    subject_id: uuid.UUID
    name: str
    outcome: Literal["existing", "created"]
    degraded: bool = False
    degraded_reason: str | None = None
