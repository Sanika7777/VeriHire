from app.core.enums import SignalSeverity, SubScoreCode
from app.integrations import company_registry, dns_checks, tls_checks, whois_rdap
from app.modules.companies.models import Company
from app.modules.verification.scoring.signals import Signal, SubScoreResult

NEW_DOMAIN_DAYS = 30
ESTABLISHED_DOMAIN_DAYS = 365


async def score_company_legitimacy(company: Company) -> SubScoreResult:
    if not company.domain:
        return SubScoreResult(
            code=SubScoreCode.COMPANY_LEGITIMACY,
            score=None,
            signals=[
                Signal(
                    code="no_domain_to_check",
                    severity=SignalSeverity.INFO,
                    title="No domain to verify",
                    detail="This company has no website domain on file, so registry and "
                    "domain checks could not run.",
                )
            ],
        )

    domain = company.domain
    signals: list[Signal] = []
    points = 0
    checks_run = 0

    domain_age = await whois_rdap.check_domain_age(domain)
    if domain_age.checked and domain_age.age_days is not None:
        checks_run += 1
        if domain_age.age_days < NEW_DOMAIN_DAYS:
            signals.append(
                Signal(
                    code="domain_recently_registered",
                    severity=SignalSeverity.HIGH,
                    title="Domain registered very recently",
                    detail=f"{domain} was registered {domain_age.age_days} day(s) ago.",
                )
            )
        else:
            points += 30
            if domain_age.age_days >= ESTABLISHED_DOMAIN_DAYS:
                signals.append(
                    Signal(
                        code="domain_established",
                        severity=SignalSeverity.INFO,
                        title="Domain has an established history",
                        detail=f"{domain} was registered {domain_age.age_days} days ago.",
                    )
                )
    else:
        signals.append(
            Signal(
                code="domain_age_unavailable",
                severity=SignalSeverity.INFO,
                title="Domain age could not be verified",
                detail=domain_age.error or "RDAP lookup did not return a registration date.",
            )
        )

    dns_report = await dns_checks.check_domain(domain)
    if dns_report.checked:
        checks_run += 1
        if dns_report.has_mx:
            points += 15
        else:
            signals.append(
                Signal(
                    code="no_mx_records",
                    severity=SignalSeverity.HIGH,
                    title="Domain has no mail servers",
                    detail=f"{domain} has no MX records — it cannot receive email.",
                )
            )
        if dns_report.has_spf and dns_report.has_dmarc:
            points += 15
            signals.append(
                Signal(
                    code="email_auth_configured",
                    severity=SignalSeverity.INFO,
                    title="SPF and DMARC configured",
                    detail=f"{domain} has both SPF and DMARC records — consistent with a "
                    "real operating mail system.",
                )
            )
        elif dns_report.has_mx:
            signals.append(
                Signal(
                    code="email_auth_missing",
                    severity=SignalSeverity.MEDIUM,
                    title="No SPF/DMARC configured",
                    detail=f"{domain} accepts mail but has no SPF or DMARC records.",
                )
            )
    else:
        signals.append(
            Signal(
                code="dns_check_unavailable",
                severity=SignalSeverity.INFO,
                title="DNS could not be checked",
                detail=dns_report.error or "DNS lookup failed.",
            )
        )

    tls_report = await tls_checks.check_certificate(domain)
    if tls_report.checked:
        checks_run += 1
        points += 15
        if tls_report.age_days is not None and tls_report.age_days < NEW_DOMAIN_DAYS:
            signals.append(
                Signal(
                    code="tls_cert_recent",
                    severity=SignalSeverity.MEDIUM,
                    title="TLS certificate is very new",
                    detail=f"The HTTPS certificate for {domain} was issued "
                    f"{tls_report.age_days} day(s) ago.",
                )
            )
    else:
        signals.append(
            Signal(
                code="tls_unavailable",
                severity=SignalSeverity.MEDIUM,
                title="Site is not reachable over HTTPS",
                detail=tls_report.error or f"Could not establish a TLS connection to {domain}.",
            )
        )

    registry = await company_registry.check_company_registry(company.name)
    if registry.checked:
        checks_run += 1
        if registry.matched:
            points += 25
            signals.append(
                Signal(
                    code="registry_match",
                    severity=SignalSeverity.INFO,
                    title="Company registry match found",
                    detail=f"Found a matching registration in {registry.jurisdiction}.",
                )
            )
        else:
            signals.append(
                Signal(
                    code="registry_no_match",
                    severity=SignalSeverity.MEDIUM,
                    title="No company registry match",
                    detail="No matching business registration was found.",
                )
            )
    else:
        signals.append(
            Signal(
                code="registry_check_unavailable",
                severity=SignalSeverity.INFO,
                title="Registry lookup unavailable",
                detail=registry.error or "Company registry integration is not configured.",
            )
        )

    if checks_run == 0:
        return SubScoreResult(code=SubScoreCode.COMPANY_LEGITIMACY, score=None, signals=signals)

    return SubScoreResult(
        code=SubScoreCode.COMPANY_LEGITIMACY, score=min(points, 100), signals=signals
    )
