import secrets
import uuid
from datetime import UTC, datetime

import dns.asyncresolver
import dns.exception
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ClaimMethod, ClaimStatus, EntityStatus
from app.core.errors import ConflictError, NotFoundError, UnauthorizedError
from app.modules.companies.models import Company, EntityClaim
from app.modules.companies.repository import CompanyRepository
from app.modules.users.models import User

TXT_PREFIX = "verihire-verify="


class CompanyClaimService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.companies = CompanyRepository(session)

    async def start_claim(
        self, company_id: uuid.UUID, user: User, method: ClaimMethod
    ) -> EntityClaim:
        company = await self.companies.get_by_id(company_id)
        if company is None:
            raise NotFoundError("Company not found.")
        if not company.domain:
            raise ConflictError("This company has no domain on file to verify against.")

        if method == ClaimMethod.EMAIL_DOMAIN and not user.email.lower().endswith(
            f"@{company.domain.lower()}"
        ):
            raise UnauthorizedError(
                f"Your account email must use the @{company.domain} domain for this method."
            )

        token = secrets.token_urlsafe(16)
        claim = EntityClaim(
            company_id=company.id,
            user_id=user.id,
            method=method,
            verification_token=token,
            status=ClaimStatus.PENDING,
        )
        self.session.add(claim)
        await self.session.flush()

        if method == ClaimMethod.EMAIL_DOMAIN:
            # Email domain match is itself sufficient proof — approve immediately.
            await self._approve(claim, company)

        return claim

    async def verify_dns_claim(self, claim_id: uuid.UUID, user: User) -> EntityClaim:
        claim = await self._get_owned_claim(claim_id, user)
        if claim.method != ClaimMethod.DNS_TXT:
            raise ConflictError("This claim does not use the DNS TXT method.")
        if claim.status != ClaimStatus.PENDING:
            return claim

        company = await self.companies.get_by_id(claim.company_id)
        if company is None or not company.domain:
            raise NotFoundError("Company not found.")

        found = await self._check_txt_record(company.domain, claim.verification_token)
        if not found:
            raise ConflictError(
                f"No TXT record found for {company.domain} containing "
                f"{TXT_PREFIX}{claim.verification_token}. DNS changes can take time to propagate."
            )

        await self._approve(claim, company)
        return claim

    async def _check_txt_record(self, domain: str, token: str) -> bool:
        expected = f"{TXT_PREFIX}{token}"
        try:
            answers = await dns.asyncresolver.resolve(domain, "TXT", lifetime=5.0)
        except (dns.exception.DNSException, OSError):
            return False
        for rdata in answers:
            joined = b"".join(rdata.strings).decode("utf-8", errors="ignore")
            if joined == expected:
                return True
        return False

    async def _approve(self, claim: EntityClaim, company: Company) -> None:
        claim.status = ClaimStatus.APPROVED
        claim.claimed_at = datetime.now(UTC)
        company.status = EntityStatus.CLAIMED
        await self.session.flush()

    async def _get_owned_claim(self, claim_id: uuid.UUID, user: User) -> EntityClaim:
        result = await self.session.execute(
            select(EntityClaim).where(EntityClaim.id == claim_id, EntityClaim.user_id == user.id)
        )
        claim = result.scalar_one_or_none()
        if claim is None:
            raise NotFoundError("Claim not found.")
        return claim
