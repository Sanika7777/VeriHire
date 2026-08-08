"""Freezes 50 labelled examples from the test split as a regression guard.

CI (or a local `make ml.eval` run) re-scores this fixed set and fails if
PR-AUC on it drops more than 2 points versus the recorded baseline —
independent of the full test-split metrics, so a bad retrain can't hide
behind noise in a full-scale evaluation.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import average_precision_score

from src.ingest import PROCESSED_DIR, SEED

ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts" / "v1"
FIXTURE_PATH = Path(__file__).parent.parent / "artifacts" / "regression_guard.json"
FIXTURE_SIZE = 50
MAX_PR_AUC_DROP = 0.02


def build_fixture() -> None:
    test_df = pd.read_parquet(PROCESSED_DIR / "test.parquet")
    positives = test_df[test_df["fraudulent"] == 1].sample(
        n=min(FIXTURE_SIZE // 2, (test_df["fraudulent"] == 1).sum()), random_state=SEED
    )
    negatives = test_df[test_df["fraudulent"] == 0].sample(
        n=FIXTURE_SIZE - len(positives), random_state=SEED
    )
    fixture_df = pd.concat([positives, negatives]).sample(frac=1, random_state=SEED)

    model = joblib.load(ARTIFACTS_DIR / "model.joblib")
    feature_builder = joblib.load(ARTIFACTS_DIR / "feature_builder.joblib")
    features = feature_builder.transform(fixture_df)
    probabilities = model.predict_proba(features)[:, 1]
    baseline_pr_auc = average_precision_score(fixture_df["fraudulent"], probabilities)

    fixture = {
        "job_ids": fixture_df["job_id"].tolist(),
        "labels": fixture_df["fraudulent"].tolist(),
        "baseline_pr_auc": round(float(baseline_pr_auc), 4),
        "max_allowed_drop": MAX_PR_AUC_DROP,
    }
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=2))
    print(f"Wrote {FIXTURE_PATH} (baseline PR-AUC {fixture['baseline_pr_auc']})")


def check_regression() -> bool:
    fixture = json.loads(FIXTURE_PATH.read_text())
    test_df = pd.read_parquet(PROCESSED_DIR / "test.parquet")
    fixture_df = test_df[test_df["job_id"].isin(fixture["job_ids"])]

    model = joblib.load(ARTIFACTS_DIR / "model.joblib")
    feature_builder = joblib.load(ARTIFACTS_DIR / "feature_builder.joblib")
    features = feature_builder.transform(fixture_df)
    probabilities = model.predict_proba(features)[:, 1]
    current_pr_auc = average_precision_score(fixture_df["fraudulent"], probabilities)

    drop = fixture["baseline_pr_auc"] - current_pr_auc
    passed = drop <= fixture["max_allowed_drop"]
    print(
        f"Regression guard: baseline={fixture['baseline_pr_auc']}, current={current_pr_auc:.4f}, "
        f"drop={drop:.4f}, max_allowed={fixture['max_allowed_drop']} -> "
        f"{'PASS' if passed else 'FAIL'}"
    )
    return passed


if __name__ == "__main__":
    build_fixture()
    if not check_regression():
        raise SystemExit(1)
