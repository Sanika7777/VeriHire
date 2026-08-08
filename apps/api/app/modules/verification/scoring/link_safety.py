import ipaddress
from urllib.parse import urlparse

from app.core.enums import SignalSeverity, SubScoreCode
from app.integrations import url_blocklist
from app.modules.verification.scoring.signals import Signal, SubScoreResult

_SHORTENER_HOSTS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd"}
_LOW_TRUST_TLDS = {"tk", "ml", "ga", "cf", "gq", "xyz", "top", "click"}


def _is_ip_literal(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


async def score_link_safety(url: str | None) -> SubScoreResult:
    if not url:
        return SubScoreResult(
            code=SubScoreCode.LINK_SAFETY,
            score=None,
            signals=[
                Signal(
                    code="no_url_to_check",
                    severity=SignalSeverity.INFO,
                    title="No link to verify",
                    detail="This subject has no associated URL.",
                )
            ],
        )

    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    signals: list[Signal] = []
    points = 100

    if parsed.scheme != "https":
        points -= 20
        signals.append(
            Signal(
                code="not_https",
                severity=SignalSeverity.MEDIUM,
                title="Link does not use HTTPS",
                detail=f"{url} is not served over HTTPS.",
            )
        )

    if _is_ip_literal(hostname):
        points -= 40
        signals.append(
            Signal(
                code="ip_literal_host",
                severity=SignalSeverity.HIGH,
                title="Link points to a raw IP address",
                detail="Legitimate company and job sites use a domain name, not a bare IP.",
            )
        )

    if hostname in _SHORTENER_HOSTS:
        points -= 20
        signals.append(
            Signal(
                code="url_shortener",
                severity=SignalSeverity.MEDIUM,
                title="Link uses a URL shortener",
                detail=f"{hostname} hides the real destination of this link.",
            )
        )

    tld = hostname.rsplit(".", 1)[-1] if "." in hostname else ""
    if tld in _LOW_TRUST_TLDS:
        points -= 15
        signals.append(
            Signal(
                code="low_trust_tld",
                severity=SignalSeverity.LOW,
                title="Uses a TLD commonly abused for scams",
                detail=f".{tld} domains are disproportionately used for phishing.",
            )
        )

    blocklist = await url_blocklist.check_url_blocklist(url)
    if blocklist.checked:
        if blocklist.is_flagged:
            points = 0
            signals.append(
                Signal(
                    code="blocklisted",
                    severity=SignalSeverity.CRITICAL,
                    title="Flagged by Google Safe Browsing",
                    detail=f"Threat types: {', '.join(blocklist.threat_types or [])}.",
                )
            )
        else:
            signals.append(
                Signal(
                    code="not_blocklisted",
                    severity=SignalSeverity.INFO,
                    title="Not on any known blocklist",
                    detail="Google Safe Browsing found no known threats for this link.",
                )
            )
    else:
        signals.append(
            Signal(
                code="blocklist_check_unavailable",
                severity=SignalSeverity.INFO,
                title="Blocklist check unavailable",
                detail=blocklist.error or "Safe Browsing integration is not configured.",
            )
        )

    return SubScoreResult(code=SubScoreCode.LINK_SAFETY, score=max(points, 0), signals=signals)
