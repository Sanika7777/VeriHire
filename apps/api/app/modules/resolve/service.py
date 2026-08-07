import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import EntityStatus, SubjectType
from app.integrations.web_fetch import FetchBlockedByRobotsError, UnsafeUrlError, fetch_url
from app.modules.companies.models import Company
from app.modules.companies.repository import CompanyRepository
from app.modules.companies.schemas import slugify
from app.modules.postings.models import JobPosting
from app.modules.postings.repository import JobPostingRepository
from app.modules.recruiters.models import Recruiter
from app.modules.recruiters.repository import RecruiterRepository
from app.modules.resolve.schemas import ResolveResponse

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")


def _extract_title(html: str) -> str | None:
    match = _TITLE_RE.search(html)
    if not match:
        return None
    title = _WHITESPACE_RE.sub(" ", match.group(1)).strip()
    return title or None


def classify_url(url: str) -> SubjectType:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()

    if "linkedin.com" in host and path.startswith("/in/"):
        return SubjectType.RECRUITER

    job_board_hosts = ("naukri.com", "indeed.com", "internshala.com", "linkedin.com")
    if any(board in host for board in job_board_hosts) or "/job" in path or "/jobs" in path:
        return SubjectType.JOB_POSTING

    if path in ("", "/"):
        return SubjectType.COMPANY

    return SubjectType.JOB_POSTING


def _fallback_name(url: str) -> str:
    parsed = urlparse(url)
    if parsed.path and parsed.path not in ("", "/"):
        segment = parsed.path.rstrip("/").rsplit("/", 1)[-1]
        return segment.replace("-", " ").replace("_", " ").title() or (parsed.hostname or url)
    return parsed.hostname or url


@dataclass(frozen=True)
class _FetchOutcome:
    title: str | None
    degraded: bool
    degraded_reason: str | None


async def _try_fetch_title(url: str) -> _FetchOutcome:
    try:
        result = await fetch_url(url)
    except (UnsafeUrlError, FetchBlockedByRobotsError) as exc:
        return _FetchOutcome(title=None, degraded=True, degraded_reason=str(exc))
    except httpx.HTTPError as exc:
        return _FetchOutcome(title=None, degraded=True, degraded_reason=f"Fetch failed: {exc}")

    return _FetchOutcome(title=_extract_title(result.html), degraded=False, degraded_reason=None)


class ResolveService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.companies = CompanyRepository(session)
        self.recruiters = RecruiterRepository(session)
        self.postings = JobPostingRepository(session)

    async def resolve(self, url: str) -> ResolveResponse:
        subject_type = classify_url(url)
        parsed = urlparse(url)

        if subject_type is SubjectType.COMPANY:
            return await self._resolve_company(url, parsed.hostname or url)
        if subject_type is SubjectType.RECRUITER:
            return await self._resolve_recruiter(url)
        return await self._resolve_job_posting(url)

    async def _resolve_company(self, url: str, domain: str) -> ResolveResponse:
        existing = await self.companies.get_by_domain(domain)
        if existing is not None:
            return ResolveResponse(
                subject_type=SubjectType.COMPANY,
                subject_id=existing.id,
                name=existing.name,
                outcome="existing",
            )

        fetched = await _try_fetch_title(url)
        name = fetched.title or _fallback_name(url)

        base_slug = slugify(name)
        slug = base_slug
        suffix = 1
        while await self.companies.slug_exists(slug):
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        company = Company(
            name=name,
            slug=slug,
            domain=domain,
            website_url=url,
            status=EntityStatus.UNVERIFIED,
        )
        await self.companies.create(company)

        return ResolveResponse(
            subject_type=SubjectType.COMPANY,
            subject_id=company.id,
            name=company.name,
            outcome="created",
            degraded=fetched.degraded,
            degraded_reason=fetched.degraded_reason,
        )

    async def _resolve_recruiter(self, url: str) -> ResolveResponse:
        existing = await self.recruiters.get_by_linkedin_url(url)
        if existing is not None:
            return ResolveResponse(
                subject_type=SubjectType.RECRUITER,
                subject_id=existing.id,
                name=existing.full_name,
                outcome="existing",
            )

        fetched = await _try_fetch_title(url)
        name = fetched.title or _fallback_name(url)

        recruiter = Recruiter(
            full_name=name,
            linkedin_url=url,
            status=EntityStatus.UNVERIFIED,
        )
        await self.recruiters.create(recruiter)

        return ResolveResponse(
            subject_type=SubjectType.RECRUITER,
            subject_id=recruiter.id,
            name=recruiter.full_name,
            outcome="created",
            degraded=fetched.degraded,
            degraded_reason=fetched.degraded_reason,
        )

    async def _resolve_job_posting(self, url: str) -> ResolveResponse:
        existing = await self.postings.get_by_source_url(url)
        if existing is not None:
            return ResolveResponse(
                subject_type=SubjectType.JOB_POSTING,
                subject_id=existing.id,
                name=existing.title,
                outcome="existing",
            )

        fetched = await _try_fetch_title(url)
        title = fetched.title or _fallback_name(url)

        posting = JobPosting(
            title=title,
            description=fetched.title or "Description unavailable — the source page could not be fetched.",
            source_url=url,
            status=EntityStatus.UNVERIFIED,
        )
        await self.postings.create(posting)

        return ResolveResponse(
            subject_type=SubjectType.JOB_POSTING,
            subject_id=posting.id,
            name=posting.title,
            outcome="created",
            degraded=fetched.degraded,
            degraded_reason=fetched.degraded_reason,
        )
