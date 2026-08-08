from app.core.enums import SubScoreCode, TrustBand
from app.modules.verification.scoring.signals import SubScoreResult

DEFAULT_WEIGHTS: dict[str, float] = {
    SubScoreCode.IDENTITY.value: 0.20,
    SubScoreCode.COMPANY_LEGITIMACY.value: 0.25,
    SubScoreCode.CONTENT_RISK.value: 0.30,
    SubScoreCode.LINK_SAFETY.value: 0.10,
    SubScoreCode.COMMUNITY_SIGNAL.value: 0.15,
}

HIGH_RISK_MAX = 39
CAUTION_MAX = 69
CONFIRMED_FRAUD_SCORE_CAP = 25


def band_for_score(score: int) -> TrustBand:
    if score <= HIGH_RISK_MAX:
        return TrustBand.HIGH_RISK
    if score <= CAUTION_MAX:
        return TrustBand.CAUTION
    return TrustBand.TRUSTED


class AggregateResult:
    def __init__(
        self,
        score: int | None,
        band: TrustBand,
        hard_override_reason: str | None,
        sub_scores: dict[str, int | None],
    ) -> None:
        self.score = score
        self.band = band
        self.hard_override_reason = hard_override_reason
        self.sub_scores = sub_scores


def aggregate(
    sub_score_results: list[SubScoreResult],
    weights: dict[str, float] | None = None,
    *,
    has_confirmed_fraud: bool,
) -> AggregateResult:
    """Combines sub-scores per CLAUDE.md §5.

    Weights are renormalized over whichever sub-scores actually have data —
    a cold-start entity missing community_signal shouldn't be penalized for
    a category no one could have populated yet. A confirmed fraud report
    hard-caps the score regardless of every other input.
    """
    weights = weights or DEFAULT_WEIGHTS
    sub_scores_by_code = {r.code.value: r.score for r in sub_score_results}

    weighted_sum = 0.0
    weight_total = 0.0
    for code, score in sub_scores_by_code.items():
        if score is None:
            continue
        weight = weights.get(code, 0.0)
        weighted_sum += score * weight
        weight_total += weight

    if weight_total == 0:
        score = None
        band = TrustBand.UNRATED
    else:
        score = round(weighted_sum / weight_total)
        band = band_for_score(score)

    hard_override_reason = None
    if has_confirmed_fraud:
        score = min(score if score is not None else CONFIRMED_FRAUD_SCORE_CAP, CONFIRMED_FRAUD_SCORE_CAP)
        band = TrustBand.HIGH_RISK
        hard_override_reason = "Capped at 25 due to a confirmed fraud report."

    return AggregateResult(
        score=score,
        band=band,
        hard_override_reason=hard_override_reason,
        sub_scores=sub_scores_by_code,
    )
