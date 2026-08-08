"""SHAP explanations for the trained LightGBM model.

TreeExplainer is fast enough to run here (offline, for the report) but a
full SHAP pass over ~40k sparse dimensions is too slow for per-request API
latency — the API instead uses a fast rule-based approximation
(app/modules/verification/scoring/ml_content_risk.py) and this is used only
to validate that approximation against ground truth at training time.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from src.ingest import PROCESSED_DIR

ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts" / "v1"
SAMPLE_SIZE = 300


def top_global_features(n: int = 20) -> list[tuple[str, float]]:
    model = joblib.load(ARTIFACTS_DIR / "model.joblib")
    feature_builder = joblib.load(ARTIFACTS_DIR / "feature_builder.joblib")
    test_df = pd.read_parquet(PROCESSED_DIR / "test.parquet")

    sample = test_df.sample(n=min(SAMPLE_SIZE, len(test_df)), random_state=42)
    features = feature_builder.transform(sample)
    feature_names = feature_builder.feature_names()

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(features)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]  # positive class

    mean_abs = np.abs(shap_values).mean(axis=0)
    mean_abs = np.asarray(mean_abs).ravel()
    top_idx = np.argsort(mean_abs)[::-1][:n]

    return [(feature_names[i], round(float(mean_abs[i]), 5)) for i in top_idx]


if __name__ == "__main__":
    top = top_global_features()
    print(json.dumps(top, indent=2))
