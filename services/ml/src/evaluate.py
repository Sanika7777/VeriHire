"""Writes services/ml/REPORTS.md from the artifacts produced by train.py."""

import json
from pathlib import Path

ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts" / "v1"
REPORTS_PATH = Path(__file__).parent.parent / "REPORTS.md"


def build_report() -> str:
    metrics = json.loads((ARTIFACTS_DIR / "metrics.json").read_text())
    test = metrics["test"]

    try:
        from src.explain import top_global_features  # noqa: PLC0415

        top_features = top_global_features(n=15)
        shap_section = "\n".join(f"- `{name}`: {value}" for name, value in top_features)
    except Exception as exc:  # noqa: BLE001
        shap_section = f"_SHAP explanation generation failed: {exc}_"

    cm = test["confusion_matrix"]
    return f"""# VeriHire content-risk model — REPORTS.md

Model version: `{metrics["model_version"]}` · seed `{metrics["seed"]}`

Trained on the EMSCAD Real/Fake Job Posting dataset (University of the
Aegean, Laboratory of Information & Communication Systems Security),
distributed via Kaggle under CC0. See `DATA.md` for provenance and known
limitations.

## Why accuracy is not reported

The dataset is ~4.8% positive (fraudulent). A model that always predicts
"legitimate" would be ~95% "accurate" while catching zero scams — accuracy
is a meaningless metric here. We report **PR-AUC**, **precision/recall at
the tuned operating threshold**, and the full confusion matrix instead.

## Headline metrics (held-out test split, never touched during fitting or
threshold tuning)

| Metric | Value |
|---|---|
| PR-AUC | {test["pr_auc"]} |
| ROC-AUC | {test["roc_auc"]} |
| Precision @ threshold | {test["precision"]} |
| Recall @ threshold | {test["recall"]} |
| F1 @ threshold | {test["f1"]} |
| Operating threshold | {metrics["operating_threshold"]} |

Baseline (LogisticRegression, TF-IDF only) validation PR-AUC:
{metrics["baseline_val_pr_auc"]} — main model (LightGBM, TF-IDF + engineered
features) validation PR-AUC: {metrics["main_val_pr_auc"]}. The main model is
the one served.

## Confusion matrix (test split, n={test["support_total"]}, positives={test["support_positive"]})

|                | Predicted legit | Predicted fraud |
|---|---|---|
| **Actual legit** | {cm[0][0]} | {cm[0][1]} |
| **Actual fraud** | {cm[1][0]} | {cm[1][1]} |

The threshold was tuned on the *validation* split's precision-recall curve
to target ≥90% precision — a false accusation against a real recruiter is
worse than missing a scam (DATA.md §7) — then evaluated once on test.

## Top global feature importances (mean |SHAP|, LightGBM, sample of test set)

{shap_section}

## Limitations

- Predominantly English-language and US-skewed (collected 2012–2014).
  Expect degraded performance on Indian regional postings, Hinglish, and
  modern scam patterns (Telegram task scams, crypto payment demands,
  deepfaked interviews) that are underrepresented in this data.
- This model is one of five Trust Score inputs (30% weight) — it is never
  the sole basis for a verdict, and a confirmed human-reviewed fraud report
  always overrides it.
- Runtime API explanations use a fast rule-based approximation of the
  training-time SHAP analysis above (see
  `apps/api/app/modules/verification/scoring/ml_content_risk.py`) — full
  per-request SHAP over this feature space would exceed the verification
  latency budget (p95 < 4s warm).
"""


if __name__ == "__main__":
    report = build_report()
    REPORTS_PATH.write_text(report)
    print(f"Wrote {REPORTS_PATH}")
