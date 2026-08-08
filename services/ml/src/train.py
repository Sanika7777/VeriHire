"""Train baseline (calibrated LinearSVC) + main (LightGBM) fraud models.

Threshold is tuned on the validation PR curve for high precision — a false
accusation against a real recruiter is worse than missing a scam
(DATA.md §7) — then the chosen operating point is evaluated once, on the
untouched test split.
"""

import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.features import FeatureBuilder
from src.ingest import PROCESSED_DIR, SEED

ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts"
TARGET_PRECISION = 0.90
MODEL_VERSION = "v1"


def _load_split(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `make ml.data` first.")
    return pd.read_parquet(path)


def _tune_threshold_for_precision(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    precision, _recall, thresholds = precision_recall_curve(y_true, y_prob)
    # precision_recall_curve returns len(thresholds) == len(precision) - 1
    candidates = [
        (t, p) for t, p in zip(thresholds, precision[:-1], strict=False) if p >= TARGET_PRECISION
    ]
    if not candidates:
        # Nothing hits the target precision — fall back to the highest
        # achievable precision rather than crashing.
        best_idx = int(np.argmax(precision[:-1]))
        return float(thresholds[best_idx])
    return float(min(t for t, _ in candidates))


def train() -> dict:
    train_df = _load_split("train")
    val_df = _load_split("val")
    test_df = _load_split("test")

    builder = FeatureBuilder()
    x_train = builder.fit_transform(train_df)
    x_val = builder.transform(val_df)
    x_test = builder.transform(test_df)

    y_train = train_df["fraudulent"].to_numpy()
    y_val = val_df["fraudulent"].to_numpy()
    y_test = test_df["fraudulent"].to_numpy()

    # Baseline: linear model with a native probability output (class_weight
    # handles the ~5% positive rate). liblinear's dual solver converges fast
    # even at ~40k sparse dimensions, unlike LinearSVC + CV-based calibration.
    baseline = LogisticRegression(
        class_weight="balanced", random_state=SEED, max_iter=1000, solver="liblinear"
    )
    baseline.fit(x_train, y_train)
    baseline_val_prob = baseline.predict_proba(x_val)[:, 1]
    baseline_pr_auc = average_precision_score(y_val, baseline_val_prob)

    # Main model: LightGBM over the same feature matrix.
    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    model = lgb.LGBMClassifier(
        n_estimators=150,
        learning_rate=0.1,
        num_leaves=31,
        scale_pos_weight=scale_pos_weight,
        random_state=SEED,
        verbosity=-1,
        n_jobs=4,
    )
    model.fit(x_train, y_train)
    val_prob = model.predict_proba(x_val)[:, 1]
    main_pr_auc = average_precision_score(y_val, val_prob)

    threshold = _tune_threshold_for_precision(y_val, val_prob)

    test_prob = model.predict_proba(x_test)[:, 1]
    test_pred = (test_prob >= threshold).astype(int)

    metrics = {
        "model_version": MODEL_VERSION,
        "seed": SEED,
        "baseline_val_pr_auc": round(float(baseline_pr_auc), 4),
        "main_val_pr_auc": round(float(main_pr_auc), 4),
        "operating_threshold": round(threshold, 4),
        "test": {
            "pr_auc": round(float(average_precision_score(y_test, test_prob)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, test_prob)), 4),
            "precision": round(float(precision_score(y_test, test_pred)), 4),
            "recall": round(float(recall_score(y_test, test_pred)), 4),
            "f1": round(float(f1_score(y_test, test_pred)), 4),
            "confusion_matrix": confusion_matrix(y_test, test_pred).tolist(),
            "support_positive": int(y_test.sum()),
            "support_total": int(len(y_test)),
        },
    }

    version_dir = ARTIFACTS_DIR / MODEL_VERSION
    version_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, version_dir / "model.joblib")
    joblib.dump(baseline, version_dir / "baseline.joblib")
    joblib.dump(builder, version_dir / "feature_builder.joblib")
    (version_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (version_dir / "threshold.json").write_text(
        json.dumps({"threshold": threshold, "model_version": MODEL_VERSION}, indent=2)
    )

    return metrics


if __name__ == "__main__":
    result = train()
    print(json.dumps(result, indent=2))
