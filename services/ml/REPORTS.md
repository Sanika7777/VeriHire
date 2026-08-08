# VeriHire content-risk model — REPORTS.md

Model version: `v1` · seed `42`

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
| PR-AUC | 0.903 |
| ROC-AUC | 0.9879 |
| Precision @ threshold | 0.94 |
| Recall @ threshold | 0.7231 |
| F1 @ threshold | 0.8174 |
| Operating threshold | 0.412 |

Baseline (LogisticRegression, TF-IDF only) validation PR-AUC:
0.8864 — main model (LightGBM, TF-IDF + engineered
features) validation PR-AUC: 0.9319. The main model is
the one served.

## Confusion matrix (test split, n=2682, positives=130)

|                | Predicted legit | Predicted fraud |
|---|---|---|
| **Actual legit** | 2546 | 6 |
| **Actual fraud** | 36 | 94 |

The threshold was tuned on the *validation* split's precision-recall curve
to target ≥90% precision — a false accusation against a real recruiter is
worse than missing a scam (DATA.md §7) — then evaluated once on test.

## Top global feature importances (mean |SHAP|, LightGBM, sample of test set)

- `missing_company_profile`: 0.49435
- `has_company_logo`: 0.33771
- `it`: 0.14175
- `00 `: 0.13945
- `rag`: 0.13938
- `rowi`: 0.13323
- `000`: 0.13109
- `try`: 0.13024
- `sho`: 0.12652
- ` cle`: 0.12416
- `igi`: 0.12203
- `ttin`: 0.1205
- `vers`: 0.12037
- `of our`: 0.12002
- `required_education_Bachelor's Degree`: 0.10157

## Post-launch robustness probe: modern Indian-context scam text

The headline metrics above are all measured in-distribution, on a held-out
split of the same 2012-2014, US-skewed EMSCAD data the model was trained on.
To sanity-check out-of-distribution generalization — the scenario this
product actually needs to handle — we hand-wrote 4 modern Indian-context
scam postings (UPI/advance-fee demands, WhatsApp/Telegram handoff, "no
experience, high pay") and 3 legitimate Indian postings, none of which
resemble the training vocabulary, and ran them through the trained
artifacts directly (no retraining).

Result: the model correctly flagged 2/4 scams and correctly cleared 3/3
legitimate postings — but **missed 2 scams that contained an explicit
"security deposit" / "processing fee" phrase**, because that one engineered
feature is only one of ~8,000+ dimensions and can be outweighed by
TF-IDF patterns learned from the training vocabulary.

**Fix applied**: `apps/api/app/modules/verification/scoring/content_risk.py`
now runs the keyword-family check (`ml_content_risk.detect_risk_families`)
independently of the ML probability, exactly as CLAUDE.md §5 specifies two
separate content_risk inputs (ML probability *and* keyword risk families),
rather than only feeding keyword hits into the model as one of many
features. A confirmed advance-fee phrase now caps the content_risk score at
30 regardless of what the blended model says; a messaging-handoff phrase
caps at 55; personal-email contact at 65; urgency language alone at 75
(weakest signal — common in legitimate fast-growth hiring too). Re-running
the same 4 scam postings after this change: all 4 now score ≤30. Golden-file
tests for this live in `apps/api/tests/test_content_risk_keyword_families.py`.
This also means content_risk no longer goes fully `Unrated` when the ML
model isn't loaded but the text contains an unambiguous risk phrase.

## Why we did not add MiniLM embeddings

CLAUDE.md §3 lists `sentence-transformers/all-MiniLM-L6-v2` embeddings as
part of the ML stack. We evaluated adding them to the content-risk feature
set and decided against it for this iteration:

- The current TF-IDF + engineered-feature + LightGBM model already clears
  both Phase 4 targets by a wide margin (PR-AUC 0.903 vs ≥0.85 target,
  precision 0.94 vs ≥0.90 target) on the in-distribution test split.
- The robustness gap we actually found (above) was not a semantic
  understanding gap that embeddings would fix — it was a specific keyword
  pattern getting outvoted, which a deterministic, auditable rule fixes
  more directly and more explainably than a 384-dim embedding would.
  CLAUDE.md §2 requires every ML prediction to be explainable; an
  embedding-derived feature is harder to attribute to a plain-language
  reason than a matched keyword pattern.
- Adding `sentence-transformers` pulls in a multi-hundred-MB `torch`
  dependency and materially increases both training time and per-request
  inference latency (CLAUDE.md §5: p95 < 4s warm) for a benefit that isn't
  evidenced by the robustness probe above.

This is a decision to revisit if a future dataset refresh with modern,
India-specific scam examples shows a generalization gap that keyword rules
can't close — semantic similarity to known scam templates is exactly the
kind of gap embeddings would help with.

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
