import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import EntityStatus


class RecruiterCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    company_id: uuid.UUID | None = None
    headline: str | None = Field(default=None, max_length=300)
    email: str | None = Field(default=None, max_length=320)
    linkedin_url: str | None = Field(default=None, max_length=2048)
    bio: str | None = None
    profile_created_on: date | None = None


class RecruiterUpdate(BaseModel):
    headline: str | None = Field(default=None, max_length=300)
    photo_url: str | None = Field(default=None, max_length=2048)
    bio: str | None = None


class RecruiterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    full_name: str
    headline: str | None
    email: str | None
    linkedin_url: str | None
    photo_url: str | None
    bio: str | None
    status: EntityStatus
    created_at: datetime
    updated_at: datetime
