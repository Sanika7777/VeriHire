import math
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ReportStatus, SignalSeverity, SubjectType, SubScoreCode
from app.modules.reports.models import Report
from app.modules.reviews.models import Review
from app.modules.verification.scoring.signals import Signal, SubScoreResult

REPORT_DECAY_HALF_LIFE_DAYS = 90


def _wilson_lower_bound(positive: int, total: int, z: float = 1.96) -> float:
    if total == 0:
        return 0.0
    phat = positive / total
    denominator = 1 + z**2 / total
    centre = phat + z**2 / (2 * total)
    margin = z * math.sqrt((phat * (1 - phat) + z**2 / (4 * total)) / total)
    return (centre - margin) / denominator


async def score_community_signal(
    session: AsyncSession, subject_type: SubjectType, subject_id: uuid.UUID
) -> SubScoreResult:
    reports_result = await session.execute(
        select(Report.status, Report.created_at).where(
            Report.subject_type == subject_type,
            Report.subject_id == subject_id,
            Report.deleted_at.is_(None),
        )
    )
    reports = reports_result.all()

    reviews_result = await session.execute(
        select(
            Review.rating_communication,
            Review.rating_process_transparency,
            Review.rating_offer_accuracy,
            Review.rating_professionalism,
        ).where(
            Review.subject_type == subject_type,
            Review.subject_id == subject_id,
            Review.deleted_at.is_(None),
        )
    )
    reviews = reviews_result.all()

    if not reports and not reviews:
        return SubScoreResult(
            code=SubScoreCode.COMMUNITY_SIGNAL,
            score=None,
            signals=[
                Signal(
                    code="no_community_data",
                    severity=SignalSeverity.INFO,
                    title="No community activity yet",
                    detail="No reports or reviews have been submitted for this subject.",
                )
            ],
        )

    signals: list[Signal] = []
    points = 70.0  # midpoint when only weak/no signal is present

    confirmed = [r for r in reports if r.status == ReportStatus.CONFIRMED]
    if confirmed:
        now = datetime.now(UTC)
        decayed_weight = sum(
            0.5 ** ((now - r.created_at).days / REPORT_DECAY_HALF_LIFE_DAYS) for r in confirmed
        )
        points -= min(decayed_weight * 25, 70)
        signals.append(
            Signal(
                code="confirmed_fraud_reports",
                severity=SignalSeverity.CRITICAL,
                title=f"{len(confirmed)} confirmed fraud report(s)",
                detail="The moderation team has confirmed at least one fraud report "
                "against this subject.",
            )
        )
    elif reports:
        pending = len(reports)
        points -= min(pending * 5, 20)
        signals.append(
            Signal(
                code="pending_reports",
                severity=SignalSeverity.MEDIUM,
                title=f"{pending} unconfirmed report(s) under review",
                detail="These reports have not yet been reviewed by moderators.",
            )
        )

    if reviews:
        averages = [
            (r.rating_communication + r.rating_process_transparency + r.rating_offer_accuracy
             + r.rating_professionalism) / 4
            for r in reviews
        ]
        positive = sum(1 for a in averages if a >= 4)
        wilson = _wilson_lower_bound(positive, len(averages))
        review_points = wilson * 100
        points = points * 0.5 + review_points * 0.5
        mean_rating = sum(averages) / len(averages)
        signals.append(
            Signal(
                code="review_summary",
                severity=SignalSeverity.INFO,
                title=f"{len(reviews)} review(s), average {mean_rating:.1f}/5",
                detail="Community review ratings across communication, transparency, "
                "offer accuracy and professionalism.",
            )
        )

    return SubScoreResult(
        code=SubScoreCode.COMMUNITY_SIGNAL,
        score=max(0, min(round(points), 100)),
        signals=signals,
    )
