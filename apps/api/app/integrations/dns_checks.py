"""DNS-based company legitimacy signals: does this domain actually run mail?

Free, fast, and a very high signal per DATA.md — scam "companies" rarely
configure SPF/DMARC even when they do have MX records.
"""

from dataclasses import dataclass

import dns.asyncresolver
import dns.exception

DNS_TIMEOUT_SECONDS = 4.0


@dataclass(frozen=True)
class DnsReport:
    checked: bool
    has_mx: bool = False
    has_spf: bool = False
    has_dmarc: bool = False
    error: str | None = None


async def _lookup_txt_prefix(domain: str, prefix: str) -> bool:
    try:
        answers = await dns.asyncresolver.resolve(domain, "TXT", lifetime=DNS_TIMEOUT_SECONDS)
    except (dns.exception.DNSException, OSError):
        return False
    for rdata in answers:
        joined = b"".join(rdata.strings).decode("utf-8", errors="ignore")
        if joined.lower().startswith(prefix):
            return True
    return False


async def check_domain(domain: str) -> DnsReport:
    try:
        mx_answers = await dns.asyncresolver.resolve(domain, "MX", lifetime=DNS_TIMEOUT_SECONDS)
        has_mx = len(mx_answers) > 0
    except dns.resolver.NXDOMAIN:
        return DnsReport(checked=True, has_mx=False, has_spf=False, has_dmarc=False)
    except (dns.exception.DNSException, OSError) as exc:
        return DnsReport(checked=False, error=str(exc))

    has_spf = await _lookup_txt_prefix(domain, "v=spf1")
    has_dmarc = await _lookup_txt_prefix(f"_dmarc.{domain}", "v=dmarc1")

    return DnsReport(checked=True, has_mx=has_mx, has_spf=has_spf, has_dmarc=has_dmarc)
