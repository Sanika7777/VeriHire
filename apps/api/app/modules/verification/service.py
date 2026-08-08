import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubjectType, SubScoreCode, TrustBand, VerificationStatus
from app.core.errors import NotFoundError
from app.modules.companies.repository import CompanyRepository
from app.modules.postings.repository import JobPostingRepository
from app.modules.recruiters.repository import RecruiterRepository
from app.modules.verification.models import ScoringConfig, Verification, VerificationSignal
from app.modules.verification.repository import VerificationRepository
from app.modules.verification.scoring import (
    company_legitimacy,
    content_risk,
    identity,
    link_safety,
)
from app.modules.verification.scoring.aggregator import DEFAULT_WEIGHTS, aggregate
from app.modules.verification.scoring.community_signal import score_community_signal
from app.modules.verification.scoring.signals import SubScoreResult

MODEL_VERSION = "v1"


class VerificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = VerificationRepository(session)
        self.companies = CompanyRepository(session)
        self.recruiters = RecruiterRepository(session)
        self.postings = JobPostingRepository(session)

    async def get_by_id(self, verification_id: uuid.UUID) -> Verification:
        verification = await self.repo.get_by_id(verification_id)
        if verification is None:
            raise NotFoundError("Verification not found.")
        return verification

    async def get_latest(
        self, subject_type: SubjectType, subject_id: uuid.UUID
    ) -> Verification | None:
        return await self.repo.get_latest(subject_type, subject_id)

    async def get_history(
        self, subject_type: SubjectType, subject_id: uuid.UUID
    ) -> list[Verification]:
        return await self.repo.get_history(subject_type, subject_id)

    async def create_pending(
        self, subject_type: SubjectType, subject_id: uuid.UUID, requested_by_user_id: uuid.UUID | None
    ) -> Verification:
        verification = Verification(
            subject_type=subject_type,
            subject_id=subject_id,
            band=TrustBand.UNRATED,
            sub_scores={},
            signals=[],
            status=VerificationStatus.PENDING,
            requested_by_user_id=requested_by_user_id,
        )
        return await self.repo.create(verification)

    async def _active_weights(self) -> tuple[dict[str, float], int | None]:
        config = await self.get_active_scoring_config()
        return config.weights, config.version

    async def get_active_scoring_config(self) -> ScoringConfig:
        config = await self.repo.get_active_scoring_config()
        if config is None:
            next_version = await self.repo.next_scoring_config_version()
            config = ScoringConfig(
                version=next_version,
                weights=DEFAULT_WEIGHTS,
                thresholds={},
                is_active=True,
                published_at=datetime.now(UTC),
            )
            await self.repo.create_scoring_config(config)
        return config

    async def preview_weight_change(
        self, new_weights: dict[str, float], *, sample_size: int = 100
    ) -> dict[str, object]:
        """Recomputes aggregate scores for a sample of recent verifications
        against `new_weights`, reusing their already-stored sub_scores —
        cheap, no need to re-run any calculator (CLAUDE.md §9 Phase 9)."""
        sample = await self.repo.sample_recent_done_verifications(sample_size)

        before_scores: list[int] = []
        after_scores: list[int] = []
        band_shifts: dict[str, int] = {}

        for verification in sample:
            if verification.score is None:
                continue
            before_scores.append(verification.score)

            sub_results = [
                SubScoreResult(code=SubScoreCode(code), score=score, signals=[])
                for code, score in verification.sub_scores.items()
            ]
            has_confirmed_fraud = verification.hard_override_reason is not None
            result = aggregate(sub_results, new_weights, has_confirmed_fraud=has_confirmed_fraud)
            if result.score is None:
                continue
            after_scores.append(result.score)

            if result.band != verification.band:
                key = f"{verification.band.value}->{result.band.value}"
                band_shifts[key] = band_shifts.get(key, 0) + 1

        return {
            "sample_size": len(sample),
            "average_score_before": (
                round(sum(before_scores) / len(before_scores), 1) if before_scores else None
            ),
            "average_score_after": (
                round(sum(after_scores) / len(after_scores), 1) if after_scores else None
            ),
            "band_shifts": band_shifts,
        }

    async def publish_scoring_config(
        self,
        weights: dict[str, float],
        thresholds: dict[str, object],
        *,
        created_by: uuid.UUID | None,
    ) -> ScoringConfig:
        await self.repo.deactivate_all_scoring_configs()
        next_version = await self.repo.next_scoring_config_version()
        config = ScoringConfig(
            version=next_version,
            weights=weights,
            thresholds=thresholds,
            is_active=True,
            created_by_user_id=created_by,
            published_at=datetime.now(UTC),
        )
        return await self.repo.create_scoring_config(config)

    async def compute(self, verification_id: uuid.UUID) -> Verification:
        """Runs every applicable sub-score calculator, aggregates, and
        overwrites the pending row in place with the final result — the row
        itself stays immutable to callers once status is DONE.
        """
        verification = await self.get_by_id(verification_id)
        verification.status = VerificationStatus.RESOLVING
        await self.session.flush()

        try:
            sub_results = await self._run_calculators(
                verification.subject_type, verification.subject_id
            )
        except Exception as exc:  # noqa: BLE001
            verification.status = VerificationStatus.FAILED
            verification.error_detail = str(exc)
            await self.session.flush()
            return verification

        verification.status = VerificationStatus.SCORING
        await self.session.flush()

        has_confirmed_fraud = any(
            s.code == "confirmed_fraud_reports" for r in sub_results for s in r.signals
        )
        weights, config_version = await self._active_weights()
        result = aggregate(sub_results, weights, has_confirmed_fraud=has_confirmed_fraud)

        # Pair each signal with its originating sub-score directly, rather
        # than reverse-looking-up "which result produced this signal" —
        # two calculators could otherwise emit structurally identical
        # signals and be matched to the wrong sub-score.
        signal_pairs = [(r.code, s) for r in sub_results for s in r.signals]

        verification.score = result.score
        verification.band = result.band
        verification.sub_scores = result.sub_scores
        verification.signals = [s.to_dict(code) for code, s in signal_pairs]
        verification.model_version = MODEL_VERSION
        verification.config_version = config_version
        verification.hard_override_reason = result.hard_override_reason
        verification.status = VerificationStatus.DONE
        verification.computed_at = datetime.now(UTC)
        await self.session.flush()

        signal_rows = [
            VerificationSignal(
                verification_id=verification.id,
                sub_score_code=code,
                code=s.code,
                severity=s.severity,
                title=s.title,
                detail=s.detail,
                evidence_url=s.evidence_url,
            )
            for code, s in signal_pairs
        ]
        await self.repo.add_signal_rows(signal_rows)

        return verification

    async def _run_calculators(
        self, subject_type: SubjectType, subject_id: uuid.UUID
    ) -> list[SubScoreResult]:
        if subject_type == SubjectType.COMPANY:
            return await self._score_company(subject_id)
        if subject_type == SubjectType.RECRUITER:
            return await self._score_recruiter(subject_id)
        return await self._score_job_posting(subject_id)

    async def _score_company(self, company_id: uuid.UUID) -> list[SubScoreResult]:
        company = await self.companies.get_by_id(company_id)
        if company is None:
            raise NotFoundError("Company not found.")

        identity_result = identity.score_company_identity(company)
        legitimacy_result = await company_legitimacy.score_company_legitimacy(company)
        link_result = await link_safety.score_link_safety(company.website_url)
        content_result = content_risk.content_risk_cold_start()
        community_result = await score_community_signal(
            self.session, SubjectType.COMPANY, company_id
        )

        return [identity_result, legitimacy_result, content_result, link_result, community_result]

    async def _score_recruiter(self, recruiter_id: uuid.UUID) -> list[SubScoreResult]:
        recruiter = await self.recruiters.get_by_id(recruiter_id)
        if recruiter is None:
            raise NotFoundError("Recruiter not found.")

        company = (
            await self.companies.get_by_id(recruiter.company_id) if recruiter.company_id else None
        )

        identity_result = identity.score_recruiter_identity(recruiter, company)
        legitimacy_result = (
            await company_legitimacy.score_company_legitimacy(company)
            if company
            else SubScoreResult(code=SubScoreCode.COMPANY_LEGITIMACY, score=None, signals=[])
        )
        link_result = await link_safety.score_link_safety(recruiter.linkedin_url)
        content_result = content_risk.content_risk_cold_start()
        community_result = await score_community_signal(
            self.session, SubjectType.RECRUITER, recruiter_id
        )

        return [identity_result, legitimacy_result, content_result, link_result, community_result]

    async def _score_job_posting(self, posting_id: uuid.UUID) -> list[SubScoreResult]:
        posting = await self.postings.get_by_id(posting_id)
        if posting is None:
            raise NotFoundError("Job posting not found.")

        company = (
            await self.companies.get_by_id(posting.company_id) if posting.company_id else None
        )
        recruiter = (
            await self.recruiters.get_by_id(posting.recruiter_id) if posting.recruiter_id else None
        )

        identity_result = (
            identity.score_recruiter_identity(recruiter, company)
            if recruiter
            else identity.identity_cold_start()
        )
        legitimacy_result = (
            await company_legitimacy.score_company_legitimacy(company)
            if company
            else SubScoreResult(code=SubScoreCode.COMPANY_LEGITIMACY, score=None, signals=[])
        )
        content_result = content_risk.score_job_posting_content_risk(posting)
        link_result = await link_safety.score_link_safety(posting.source_url)
        community_result = await score_community_signal(
            self.session, SubjectType.JOB_POSTING, posting_id
        )

        return [identity_result, legitimacy_result, content_result, link_result, community_result]
