"""Loads the trained services/ml fraud model and scores posting text.

The training pipeline (services/ml) and this API are separate uv projects
with separate virtualenvs, so the pickled `FeatureBuilder` — whose class
lives at `src.features.FeatureBuilder` in the ml project — can only be
unpickled here if `services/ml` is on `sys.path` under that same `src.*`
import path. We add it once, lazily, the first time a model is loaded.
"""

import json
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings

_RISK_FEATURE_LABELS = {
    "has_personal_email": "Contact is a personal email address, not a company one",
    "has_messaging_handle": "Asks candidates to move to WhatsApp/Telegram",
    "has_advance_fee_phrase": "Mentions a registration, processing, or deposit fee",
    "has_urgency_marker": "Uses high-pressure urgency language",
    "missing_company_profile": "No company profile provided",
}


@dataclass(frozen=True)
class ContentRiskPrediction:
    probability: float
    threshold: float
    label: str
    model_version: str
    reasons: list[str]


def _apps_api_root() -> Path:
    # apps/api/app/modules/verification/scoring/ml_content_risk.py -> apps/api
    return Path(__file__).resolve().parents[4]


def _ml_service_dir() -> Path:
    settings = get_settings()
    # ml_artifacts_dir ("../../services/ml/artifacts" by default) is defined
    # relative to the apps/api project root, not to this file's own — much
    # deeper — location; its parent is the services/ml project root that
    # needs to be on sys.path for unpickling.
    return (_apps_api_root() / settings.ml_artifacts_dir).resolve().parent


@lru_cache(maxsize=1)
def _load_model_bundle() -> dict[str, Any] | None:
    ml_root = _ml_service_dir()
    artifacts_dir = ml_root / "artifacts" / "v1"

    if not artifacts_dir.exists():
        return None

    if str(ml_root) not in sys.path:
        sys.path.insert(0, str(ml_root))

    import joblib  # noqa: PLC0415

    model = joblib.load(artifacts_dir / "model.joblib")
    feature_builder = joblib.load(artifacts_dir / "feature_builder.joblib")
    threshold_data = json.loads((artifacts_dir / "threshold.json").read_text())

    return {
        "model": model,
        "feature_builder": feature_builder,
        "threshold": threshold_data["threshold"],
        "model_version": threshold_data["model_version"],
    }


def is_model_available() -> bool:
    return _load_model_bundle() is not None


def predict_content_risk(
    *,
    title: str,
    description: str,
    requirements: str | None,
    company_profile: str | None,
    has_company_logo: bool,
    has_questions: bool,
    telecommuting: bool,
    employment_type: str | None,
    required_experience: str | None,
    required_education: str | None,
) -> ContentRiskPrediction | None:
    bundle = _load_model_bundle()
    if bundle is None:
        return None

    import pandas as pd  # noqa: PLC0415

    row = pd.DataFrame(
        [
            {
                "title": title,
                "company_profile": company_profile or "",
                "description": description,
                "requirements": requirements or "",
                "has_company_logo": int(has_company_logo),
                "has_questions": int(has_questions),
                "telecommuting": int(telecommuting),
                "salary_range": None,
                "employment_type": employment_type,
                "required_experience": required_experience,
                "required_education": required_education,
            }
        ]
    )

    feature_builder = bundle["feature_builder"]
    features = feature_builder.transform(row)
    probability = float(bundle["model"].predict_proba(features)[0, 1])
    threshold = bundle["threshold"]
    label = "fraudulent" if probability >= threshold else "legitimate"

    reasons = _explain(row.iloc[0], probability)

    return ContentRiskPrediction(
        probability=round(probability, 4),
        threshold=threshold,
        label=label,
        model_version=bundle["model_version"],
        reasons=reasons,
    )


def _explain(row: "Any", probability: float) -> list[str]:  # noqa: ANN401
    """Fast, rule-based reasons for the API response.

    Full SHAP attributions are computed offline for the model report
    (services/ml/src/explain.py) — running SHAP per request against a
    ~40k-dimension TF-IDF matrix would blow the verification latency budget
    (CLAUDE.md §5: p95 < 4s warm).
    """
    text = f"{row['title']} {row['company_profile']} {row['description']} {row['requirements']}"
    reasons = [
        label
        for key, label in _RISK_FEATURE_LABELS.items()
        if key != "missing_company_profile" and _matches(key, text)
    ]
    if not row["company_profile"]:
        reasons.append(_RISK_FEATURE_LABELS["missing_company_profile"])

    if not reasons:
        reasons.append(
            "High risk based on overall language patterns in the posting"
            if probability >= 0.5
            else "No specific risk phrases detected in the posting text"
        )

    return reasons[:5]


_PATTERNS = {
    # Kept in sync with services/ml/src/features.py's engineered-feature
    # regexes so the training-time features and this serving-time,
    # ML-independent keyword check never drift apart.
    "has_personal_email": re.compile(
        r"\b[a-zA-Z0-9._%+-]+@(gmail|yahoo|hotmail|outlook|rediffmail)\.com\b", re.IGNORECASE
    ),
    "has_messaging_handle": re.compile(r"\b(whatsapp|telegram|wa\.me|t\.me)\b", re.IGNORECASE),
    "has_advance_fee_phrase": re.compile(
        r"\b(registration fee|processing fee|security deposit|"
        r"pay(?:ment)? to (?:secure|confirm)|refundable deposit|advance payment)\b",
        re.IGNORECASE,
    ),
    "has_urgency_marker": re.compile(
        r"\b(urgent(?:ly)?|immediate(?:ly)? (?:hiring|joining)|apply now|"
        r"limited (?:seats|time)|act now|hurry)\b",
        re.IGNORECASE,
    ),
}


def _matches(key: str, text: str) -> bool:
    pattern = _PATTERNS.get(key)
    return bool(pattern and pattern.search(text))


def detect_risk_families(text: str) -> list[str]:
    """Independent, rule-based keyword-family detection (CLAUDE.md §5).

    Runs regardless of whether the ML model is loaded or what it predicts —
    a real probe against modern Indian-context scam text (not represented in
    the 2012-2014 EMSCAD training data) found cases where an explicit
    advance-fee or messaging-handoff phrase was present but the blended ML
    probability alone still scored the posting as low-risk, because that one
    engineered feature was outweighed by thousands of other TF-IDF
    dimensions. Surfacing these as a separate, always-on signal — not just
    ML explanation text — closes that gap. See services/ml/REPORTS.md.
    """
    return [key for key in _PATTERNS if _matches(key, text)]
