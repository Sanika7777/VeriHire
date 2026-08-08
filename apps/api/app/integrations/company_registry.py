"""Company registry lookup (OpenCorporates / MCA). Requires an API key we
don't have in this environment — degrades to "not checked" rather than
blocking scoring, per CLAUDE.md §5 cold-start philosophy."""

from dataclasses import dataclass

import httpx

from app.core.config import get_settings

REGISTRY_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class RegistryReport:
    checked: bool
    matched: bool = False
    jurisdiction: str | None = None
    error: str | None = None


async def check_company_registry(company_name: str) -> RegistryReport:
    settings = get_settings()
    if not settings.opencorporates_api_key:
        return RegistryReport(checked=False, error="OpenCorporates API key not configured.")

    try:
        async with httpx.AsyncClient(timeout=REGISTRY_TIMEOUT_SECONDS) as client:
            response = await client.get(
                "https://api.opencorporates.com/v0.4/companies/search",
                params={
                    "q": company_name,
                    "api_token": settings.opencorporates_api_key.get_secret_value(),
                },
            )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return RegistryReport(checked=False, error=str(exc))

    companies = data.get("results", {}).get("companies", [])
    if not companies:
        return RegistryReport(checked=True, matched=False)

    top = companies[0]["company"]
    return RegistryReport(checked=True, matched=True, jurisdiction=top.get("jurisdiction_code"))
