import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import EntityStatus


class JobPostingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    company_id: uuid.UUID | None = None
    recruiter_id: uuid.UUID | None = None
    requirements: str | None = None
    benefits: str | None = None
    location_city: str | None = Field(default=None, max_length=120)
    location_country: str | None = Field(default=None, max_length=120)
    employment_type: str | None = Field(default=None, max_length=32)
    required_experience: str | None = Field(default=None, max_length=32)
    required_education: str | None = Field(default=None, max_length=32)
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = Field(default=None, max_length=8)
    telecommuting: bool = False
    has_company_logo: bool = False
    has_questions: bool = False
    source_url: str | None = Field(default=None, max_length=2048)


class JobPostingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    recruiter_id: uuid.UUID | None
    title: str
    description: str
    requirements: str | None
    benefits: str | None
    location_city: str | None
    location_country: str | None
    employment_type: str | None
    required_experience: str | None
    required_education: str | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    telecommuting: bool
    source_url: str | None
    status: EntityStatus
    posted_at: datetime | None
    created_at: datetime
