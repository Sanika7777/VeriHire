"""TLS certificate metadata via a direct handshake — no API key needed."""

import asyncio
import socket
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime

TLS_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class TlsReport:
    checked: bool
    has_valid_cert: bool = False
    issuer: str | None = None
    age_days: int | None = None
    error: str | None = None


def _parse_asn1_date(value: str) -> datetime:
    return datetime.strptime(value, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)


def _fetch_cert_sync(hostname: str) -> dict[str, object]:
    context = ssl.create_default_context()
    with context.wrap_socket(
        socket.create_connection((hostname, 443), timeout=TLS_TIMEOUT_SECONDS),
        server_hostname=hostname,
    ) as sock:
        return sock.getpeercert()  # type: ignore[return-value]


async def check_certificate(hostname: str) -> TlsReport:
    try:
        cert = await asyncio.wait_for(
            asyncio.to_thread(_fetch_cert_sync, hostname), timeout=TLS_TIMEOUT_SECONDS + 1
        )
    except (TimeoutError, OSError, ssl.SSLError) as exc:
        return TlsReport(checked=False, error=str(exc))

    raw_issuer = cert.get("issuer")
    issuer_parts = dict(x[0] for x in raw_issuer) if isinstance(raw_issuer, tuple | list) else {}
    issuer = issuer_parts.get("organizationName") or issuer_parts.get("commonName")

    not_before_raw = cert.get("notBefore")
    age_days = None
    if isinstance(not_before_raw, str):
        age_days = (datetime.now(UTC) - _parse_asn1_date(not_before_raw)).days

    return TlsReport(checked=True, has_valid_cert=True, issuer=issuer, age_days=age_days)
