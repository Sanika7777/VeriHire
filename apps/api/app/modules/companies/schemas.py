import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import EntityStatus


def slugify(name: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "-" for c in name.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "company"


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    domain: str | None = Field(default=None, max_length=255)
    website_url: str | None = Field(default=None, max_length=2048)
    description: str | None = None
    industry: str | None = Field(default=None, max_length=120)
    employee_count_range: str | None = Field(default=None, max_length=32)
    hq_city: str | None = Field(default=None, max_length=120)
    hq_country: str | None = Field(default=None, max_length=120)
    founded_year: int | None = None


class CompanyUpdate(BaseModel):
    description: str | None = None
    website_url: str | None = Field(default=None, max_length=2048)
    logo_url: str | None = Field(default=None, max_length=2048)
    industry: str | None = Field(default=None, max_length=120)
    employee_count_range: str | None = Field(default=None, max_length=32)
    hq_city: str | None = Field(default=None, max_length=120)
    hq_country: str | None = Field(default=None, max_length=120)
    founded_year: int | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    domain: str | None
    description: str | None
    logo_url: str | None
    website_url: str | None
    industry: str | None
    employee_count_range: str | None
    hq_city: str | None
    hq_country: str | None
    founded_year: int | None
    status: EntityStatus
    created_at: datetime
    updated_at: datetime
