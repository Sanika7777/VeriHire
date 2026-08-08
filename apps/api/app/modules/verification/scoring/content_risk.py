from app.core.enums import SignalSeverity, SubScoreCode
from app.modules.postings.models import JobPosting
from app.modules.verification.scoring import ml_content_risk
from app.modules.verification.scoring.signals import Signal, SubScoreResult

# High precision matters more than recall here (DATA.md §7): a false
# accusation against a real recruiter is worse than missing a scam, so we
# only escalate severity once the model clears its tuned threshold.

# Independent, ML-probability-agnostic caps for the keyword risk families
# named in CLAUDE.md §5 (advance fee, WhatsApp/Telegram handoff, personal
# email, urgency pressure). A real probe against modern Indian-context scam
# text found the blended ML model alone missing these because one engineered
# feature can get outweighed by thousands of TF-IDF dimensions learned from
# 2012-2014 US-skewed data (see services/ml/REPORTS.md) — these caps make a
# strong keyword match decisive regardless of what the ML model says.
_RISK_FAMILY_CAPS: dict[str, tuple[int, SignalSeverity, str, str, str]] = {
    "has_advance_fee_phrase": (
        30,
        SignalSeverity.CRITICAL,
        "advance_fee_language",
        "Advance-fee language detected",
        "This posting asks for an upfront registration, processing, or security "
        "deposit fee — a defining pattern of advance-fee fraud, flagged "
        "independently of the ML model's own probability.",
    ),
    "has_messaging_handle": (
        55,
        SignalSeverity.HIGH,
        "messaging_handoff",
        "Asks candidates to move to WhatsApp/Telegram",
        "Legitimate employers rarely conduct an entire hiring process over "
        "WhatsApp/Telegram; this is a common pattern for moving candidates off "
        "moderated platforms.",
    ),
    "has_personal_email": (
        65,
        SignalSeverity.MEDIUM,
        "personal_email_contact",
        "Contact is a personal email address",
        "The only listed contact is a personal address (Gmail/Yahoo/etc) rather "
        "than a company domain.",
    ),
    "has_urgency_marker": (
        75,
        SignalSeverity.LOW,
        "urgency_pressure",
        "High-pressure urgency language",
        "Phrases like 'urgent', 'apply now', or 'limited seats' create time "
        "pressure that discourages candidates from researching the employer "
        "first. Weak on its own — common in legitimate fast-growth hiring too.",
    ),
}


def _keyword_risk_signals(text: str) -> tuple[list[Signal], int | None]:
    matched = ml_content_risk.detect_risk_families(text)
    if not matched:
        return [], None

    signals = []
    cap = None
    for key in matched:
        family_cap, severity, code, title, detail = _RISK_FAMILY_CAPS[key]
        cap = family_cap if cap is None else min(cap, family_cap)
        signals.append(Signal(code=code, severity=severity, title=title, detail=detail))
    return signals, cap


def score_job_posting_content_risk(posting: JobPosting) -> SubScoreResult:
    full_text = " ".join(
        part for part in (posting.title, posting.description, posting.requirements) if part
    )
    keyword_signals, keyword_cap = _keyword_risk_signals(full_text)

    prediction = ml_content_risk.predict_content_risk(
        title=posting.title,
        description=posting.description,
        requirements=posting.requirements,
        company_profile=None,
        has_company_logo=posting.has_company_logo,
        has_questions=posting.has_questions,
        telecommuting=posting.telecommuting,
        employment_type=posting.employment_type,
        required_experience=posting.required_experience,
        required_education=posting.required_education,
    )

    if prediction is None:
        if keyword_cap is None:
            return SubScoreResult(
                code=SubScoreCode.CONTENT_RISK,
                score=None,
                signals=[
                    Signal(
                        code="model_unavailable",
                        severity=SignalSeverity.INFO,
                        title="Content model unavailable",
                        detail="The fraud-detection model has not been trained/loaded yet.",
                    )
                ],
            )
        return SubScoreResult(
            code=SubScoreCode.CONTENT_RISK,
            score=keyword_cap,
            signals=[
                *keyword_signals,
                Signal(
                    code="model_unavailable",
                    severity=SignalSeverity.INFO,
                    title="Content model unavailable — scored from keyword risk phrases only",
                    detail="The fraud-detection model has not been trained/loaded yet; this "
                    "score reflects only the rule-based risk-phrase checks above.",
                ),
            ],
        )

    # probability of fraud -> trust score (inverted, 0-100)
    score = round((1 - prediction.probability) * 100)

    severity = (
        SignalSeverity.CRITICAL
        if prediction.label == "fraudulent" and prediction.probability >= 0.85
        else SignalSeverity.HIGH
        if prediction.label == "fraudulent"
        else SignalSeverity.INFO
    )

    signals = [
        Signal(
            code="content_model_reason",
            severity=severity if prediction.label == "fraudulent" else SignalSeverity.LOW,
            title=reason,
            detail=(
                f"Model confidence this posting is fraudulent: "
                f"{prediction.probability * 100:.0f}% (model {prediction.model_version})."
            ),
        )
        for reason in prediction.reasons
    ]

    if keyword_cap is not None:
        score = min(score, keyword_cap)
    signals = signals + keyword_signals

    return SubScoreResult(code=SubScoreCode.CONTENT_RISK, score=score, signals=signals)


def content_risk_cold_start() -> SubScoreResult:
    return SubScoreResult(
        code=SubScoreCode.CONTENT_RISK,
        score=None,
        signals=[
            Signal(
                code="no_content_to_analyse",
                severity=SignalSeverity.INFO,
                title="No posting content to analyse",
                detail="This subject has no associated job posting text.",
            )
        ],
    )
