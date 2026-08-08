from app.core.enums import SignalSeverity, SubScoreCode, TrustBand
from app.modules.verification.scoring.aggregator import (
    CONFIRMED_FRAUD_SCORE_CAP,
    aggregate,
    band_for_score,
)
from app.modules.verification.scoring.signals import Signal, SubScoreResult


def _result(code: SubScoreCode, score: int | None, signals: list[Signal] | None = None) -> SubScoreResult:
    return SubScoreResult(code=code, score=score, signals=signals or [])


def test_band_boundaries() -> None:
    assert band_for_score(0) == TrustBand.HIGH_RISK
    assert band_for_score(39) == TrustBand.HIGH_RISK
    assert band_for_score(40) == TrustBand.CAUTION
    assert band_for_score(69) == TrustBand.CAUTION
    assert band_for_score(70) == TrustBand.TRUSTED
    assert band_for_score(100) == TrustBand.TRUSTED


def test_aggregate_with_all_sub_scores_present() -> None:
    results = [
        _result(SubScoreCode.IDENTITY, 80),
        _result(SubScoreCode.COMPANY_LEGITIMACY, 90),
        _result(SubScoreCode.CONTENT_RISK, 95),
        _result(SubScoreCode.LINK_SAFETY, 100),
        _result(SubScoreCode.COMMUNITY_SIGNAL, 70),
    ]
    result = aggregate(results, has_confirmed_fraud=False)
    assert result.score is not None
    assert result.band == TrustBand.TRUSTED
    assert result.hard_override_reason is None


def test_aggregate_cold_start_returns_unrated() -> None:
    results = [
        _result(SubScoreCode.IDENTITY, None),
        _result(SubScoreCode.COMPANY_LEGITIMACY, None),
        _result(SubScoreCode.CONTENT_RISK, None),
        _result(SubScoreCode.LINK_SAFETY, None),
        _result(SubScoreCode.COMMUNITY_SIGNAL, None),
    ]
    result = aggregate(results, has_confirmed_fraud=False)
    assert result.score is None
    assert result.band == TrustBand.UNRATED


def test_aggregate_renormalizes_over_available_sub_scores() -> None:
    # Only content_risk (weight 0.30) has data — it alone should determine
    # the score once renormalized, i.e. effectively weight 1.0.
    results = [
        _result(SubScoreCode.IDENTITY, None),
        _result(SubScoreCode.COMPANY_LEGITIMACY, None),
        _result(SubScoreCode.CONTENT_RISK, 60),
        _result(SubScoreCode.LINK_SAFETY, None),
        _result(SubScoreCode.COMMUNITY_SIGNAL, None),
    ]
    result = aggregate(results, has_confirmed_fraud=False)
    assert result.score == 60


def test_confirmed_fraud_hard_caps_score_and_forces_high_risk() -> None:
    results = [
        _result(SubScoreCode.IDENTITY, 95),
        _result(SubScoreCode.COMPANY_LEGITIMACY, 95),
        _result(
            SubScoreCode.CONTENT_RISK,
            95,
            [
                Signal(
                    code="confirmed_fraud_reports",
                    severity=SignalSeverity.CRITICAL,
                    title="1 confirmed fraud report(s)",
                    detail="x",
                )
            ],
        ),
        _result(SubScoreCode.LINK_SAFETY, 95),
        _result(SubScoreCode.COMMUNITY_SIGNAL, 95),
    ]
    result = aggregate(results, has_confirmed_fraud=True)
    assert result.score is not None
    assert result.score <= CONFIRMED_FRAUD_SCORE_CAP
    assert result.band == TrustBand.HIGH_RISK
    assert result.hard_override_reason is not None
