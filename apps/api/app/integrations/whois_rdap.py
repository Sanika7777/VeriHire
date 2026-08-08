"""Domain registration age via RDAP (WHOIS's structured successor).

A domain registered 11 days ago advertising a "senior" role is a strong
fraud signal (DATA.md §3). Free, no API key.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.retry import retry_with_jitter

RDAP_TIMEOUT_SECONDS = 5.0
RDAP_BOOTSTRAP_URL = "https://rdap.org/domain/{domain}"


@dataclass(frozen=True)
class DomainAgeReport:
    checked: bool
    registered_at: datetime | None = None
    age_days: int | None = None
    error: str | None = None


def _is_transient(exc: BaseException) -> bool:
    # Timeouts and connection errors are worth a retry; a definitive HTTP
    # error status (4xx/5xx) already reached the server and won't be fixed
    # by trying again immediately.
    return isinstance(exc, httpx.TimeoutException | httpx.ConnectError)


async def check_domain_age(domain: str) -> DomainAgeReport:
    async def fetch() -> httpx.Response:
        async with httpx.AsyncClient(timeout=RDAP_TIMEOUT_SECONDS) as client:
            return await client.get(
                RDAP_BOOTSTRAP_URL.format(domain=domain), follow_redirects=True
            )

    try:
        response = await retry_with_jitter(fetch, should_retry=_is_transient)
        if response.status_code == 404:
            return DomainAgeReport(checked=True, error="Domain not found in RDAP.")
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return DomainAgeReport(checked=False, error=str(exc))

    registration_event = next(
        (e for e in data.get("events", []) if e.get("eventAction") == "registration"),
        None,
    )
    if registration_event is None or "eventDate" not in registration_event:
        return DomainAgeReport(checked=True, error="No registration date in RDAP response.")

    try:
        registered_at = datetime.fromisoformat(registration_event["eventDate"].replace("Z", "+00:00"))
    except ValueError as exc:
        return DomainAgeReport(checked=True, error=str(exc))

    age_days = (datetime.now(UTC) - registered_at).days
    return DomainAgeReport(checked=True, registered_at=registered_at, age_days=age_days)
