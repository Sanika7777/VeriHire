"""URL reputation via Google Safe Browsing. Degrades to "not checked" when
no API key is configured, rather than blocking link-safety scoring."""

from dataclasses import dataclass

import httpx

from app.core.config import get_settings

SAFE_BROWSING_TIMEOUT_SECONDS = 5.0
SAFE_BROWSING_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"


@dataclass(frozen=True)
class BlocklistReport:
    checked: bool
    is_flagged: bool = False
    threat_types: list[str] | None = None
    error: str | None = None


async def check_url_blocklist(url: str) -> BlocklistReport:
    settings = get_settings()
    if not settings.safe_browsing_api_key:
        return BlocklistReport(checked=False, error="Safe Browsing API key not configured.")

    body = {
        "client": {"clientId": "verihire", "clientVersion": "1.0.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }

    try:
        async with httpx.AsyncClient(timeout=SAFE_BROWSING_TIMEOUT_SECONDS) as client:
            response = await client.post(
                SAFE_BROWSING_URL,
                params={"key": settings.safe_browsing_api_key.get_secret_value()},
                json=body,
            )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return BlocklistReport(checked=False, error=str(exc))

    matches = data.get("matches", [])
    if not matches:
        return BlocklistReport(checked=True, is_flagged=False)

    threat_types = [m["threatType"] for m in matches]
    return BlocklistReport(checked=True, is_flagged=True, threat_types=threat_types)
