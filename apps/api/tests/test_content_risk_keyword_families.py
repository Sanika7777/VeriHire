"""Golden-file tests for the content-risk keyword-family backstop.

A probe against modern Indian-context scam text (not represented in the
2012-2014 EMSCAD training data) found the blended ML probability alone
missing postings with explicit advance-fee/messaging-handoff phrases,
because one engineered feature can be outweighed by thousands of TF-IDF
dimensions (see services/ml/REPORTS.md). These fixed inputs must always
produce the capped score and signal set below, regardless of what the ML
model predicts (CLAUDE.md §9: golden-file tests for the scoring engine).
"""

from app.modules.postings.models import JobPosting
from app.modules.verification.scoring import content_risk, ml_content_risk


def _posting(**overrides: object) -> JobPosting:
    defaults: dict[str, object] = {
        "title": "Data Entry Executive",
        "description": "A great opportunity for freshers.",
        "requirements": None,
        "has_company_logo": False,
        "has_questions": False,
        "telecommuting": True,
        "employment_type": "Contract",
        "required_experience": None,
        "required_education": None,
    }
    defaults.update(overrides)
    return JobPosting(**defaults)  # type: ignore[arg-type]


def test_advance_fee_phrase_caps_score_regardless_of_ml_availability(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(ml_content_risk, "predict_content_risk", lambda **_: None)
    posting = _posting(
        description="Urgent hiring, no experience needed. A refundable registration "
        "fee of Rs 999 is required to activate your ID before training starts."
    )

    result = content_risk.score_job_posting_content_risk(posting)

    assert result.score == 30
    codes = {s.code for s in result.signals}
    assert "advance_fee_language" in codes
    assert "model_unavailable" in codes


def test_advance_fee_phrase_caps_score_even_when_ml_scores_it_low(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        ml_content_risk,
        "predict_content_risk",
        lambda **_: ml_content_risk.ContentRiskPrediction(
            probability=0.04,
            threshold=0.412,
            label="legitimate",
            model_version="v1",
            reasons=["No specific risk phrases detected in the posting text"],
        ),
    )
    posting = _posting(
        description="Security deposit of Rs 1500 required to secure your slot, "
        "fully refundable after first payout."
    )

    result = content_risk.score_job_posting_content_risk(posting)

    # ML alone would have scored this 96 (1 - 0.04); the keyword override caps it.
    assert result.score == 30
    assert any(s.code == "advance_fee_language" for s in result.signals)


def test_messaging_handoff_alone_caps_at_55_not_30(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        ml_content_risk,
        "predict_content_risk",
        lambda **_: ml_content_risk.ContentRiskPrediction(
            probability=0.10,
            threshold=0.412,
            label="legitimate",
            model_version="v1",
            reasons=["No specific risk phrases detected in the posting text"],
        ),
    )
    posting = _posting(description="Message us on Telegram to proceed with your application.")

    result = content_risk.score_job_posting_content_risk(posting)

    assert result.score == 55
    codes = {s.code for s in result.signals}
    assert codes == {"messaging_handoff", "content_model_reason"}


def test_clean_posting_is_unaffected_by_keyword_backstop(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        ml_content_risk,
        "predict_content_risk",
        lambda **_: ml_content_risk.ContentRiskPrediction(
            probability=0.02,
            threshold=0.412,
            label="legitimate",
            model_version="v1",
            reasons=["No specific risk phrases detected in the posting text"],
        ),
    )
    posting = _posting(
        title="Senior Backend Engineer",
        description="We are looking for a senior backend engineer to join our "
        "payments platform team and mentor junior engineers.",
        requirements="5+ years of backend experience with Python or Java.",
    )

    result = content_risk.score_job_posting_content_risk(posting)

    keyword_codes = {code for _, _, code, _, _ in content_risk._RISK_FAMILY_CAPS.values()}  # noqa: SLF001
    assert result.score == 98
    assert not any(s.code in keyword_codes for s in result.signals)


def test_model_unavailable_and_no_keyword_match_returns_unrated(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(ml_content_risk, "predict_content_risk", lambda **_: None)
    posting = _posting(
        title="Senior Backend Engineer",
        description="We are looking for a senior backend engineer to join our team.",
    )

    result = content_risk.score_job_posting_content_risk(posting)

    assert result.score is None
    assert result.signals[0].code == "model_unavailable"
