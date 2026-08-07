# DATA.md — VeriHire datasets

Everything the ML layer trains on, where it comes from, and how it maps into the product.

---

## 1. Primary dataset — job posting fraud

### Real / Fake Job Posting Prediction (EMSCAD)

The canonical dataset for this exact problem. Built by the Laboratory of Information & Communication Systems Security at the University of the Aegean from real job ads collected by an applicant tracking system, then hand-labelled.

| | |
|---|---|
| **Kaggle page** | https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction |
| **Original source** | http://emscad.samos.aegean.gr/ (University of the Aegean) |
| **No-login mirror** | https://raw.githubusercontent.com/abbylmm/fake_job_posting/main/data/fake_job_postings.csv |
| **File** | `fake_job_postings.csv` (~50 MB) |
| **Rows** | 17,880 job postings |
| **Fraudulent** | ~866 (≈4.8% — heavily imbalanced, which is realistic and must be handled properly) |
| **Columns** | 18 |
| **Licence** | CC0 / public domain on Kaggle. Cite the University of the Aegean in `REPORTS.md`. |

**Download (Kaggle CLI):**
```bash
pip install kaggle
# put kaggle.json in ~/.kaggle/ from your Kaggle account settings
kaggle datasets download -d shivamb/real-or-fake-fake-jobposting-prediction \
  -p services/ml/data/raw --unzip
```

**Or without a Kaggle account:**
```bash
curl -L -o services/ml/data/raw/fake_job_postings.csv \
  https://raw.githubusercontent.com/abbylmm/fake_job_posting/main/data/fake_job_postings.csv
```

### Schema

| Column | Type | Notes |
|---|---|---|
| `job_id` | int | unique id |
| `title` | text | job title |
| `location` | text | `Country, State, City` |
| `department` | text | often missing |
| `salary_range` | text | often missing — *missingness itself is predictive* |
| `company_profile` | text | **strongest single signal**; absence correlates heavily with fraud |
| `description` | text | main body |
| `requirements` | text | |
| `benefits` | text | |
| `telecommuting` | bool | |
| `has_company_logo` | bool | strong negative predictor of fraud |
| `has_questions` | bool | screening questions present |
| `employment_type` | cat | Full-time / Part-time / Contract / Temporary / Other |
| `required_experience` | cat | Internship → Executive |
| `required_education` | cat | High School → Doctorate |
| `industry` | cat | |
| `function` | cat | |
| `fraudulent` | **target** | `0` = legitimate, `1` = fraudulent |

### Known limitations — state these openly in the product and the report
- Predominantly English-language and US-skewed. It will underperform on Indian regional postings and on Hinglish/vernacular scam text.
- Collected around 2012–2014. Modern scam patterns (Telegram task scams, crypto payment demands, deepfaked video interviews) are underrepresented.
- Class imbalance at ~5% means accuracy is a meaningless metric here. Report **PR-AUC, precision and recall at the operating threshold** instead.
- Because of the age and skew, the ML model is only one of five inputs to the Trust Score. Never let it be the whole verdict.

---

## 2. Secondary dataset — malicious link detection

Powers the `link_safety` sub-score, since a large share of job scams work by getting a candidate onto a phishing page.

### PhiUSIIL Phishing URL Dataset
| | |
|---|---|
| **Kaggle** | https://www.kaggle.com/datasets/ndarvind/phiusiil-phishing-url-dataset |
| **Rows** | 235,795 (134,850 legitimate, 100,945 phishing) |
| **Features** | URL lexical + page-source derived: char continuation rate, URL–title match score, TLD legitimacy probability, and more |
| **Label** | `1` = legitimate, `0` = phishing (**note the inverted convention** — flip it during ingest) |

Lighter alternative with pre-engineered lexical features only (faster to train, no page fetching):
https://www.kaggle.com/datasets/victusadi/phishing-urls-dataset-with-extracted-features

Larger and more recent, if you want a bigger corpus:
https://www.kaggle.com/datasets/moutasmtamimi/malicious-url-detection-dataset-enhanced-2026

---

## 3. Live signal sources (not datasets — APIs queried at verification time)

These feed `identity` and `company_legitimacy`. Wrap each behind an interface with a timeout, cache and stub, per `CLAUDE.md` §5.

| Source | Use | Notes |
|---|---|---|
| **RDAP / WHOIS** | Domain registration age | Free. A domain registered 11 days ago advertising a "senior" role is a strong signal. |
| **DNS records (MX, SPF, DMARC)** | Does the company actually operate email at this domain? | Free, fast, very high signal. Scam "companies" rarely configure DMARC. |
| **TLS certificate metadata** | Cert issuer and age | Free via the TLS handshake. |
| **OpenCorporates** | Company registry match across jurisdictions | Free tier available; register for an API key. |
| **MCA / data.gov.in** | Indian company registration data | Useful for the India-first positioning; check current availability and terms. |
| **Google Safe Browsing API** | URL blocklist | Free tier, generous quota. |
| **Certificate Transparency logs (crt.sh)** | Detect lookalike domains registered against a verified brand — powers impersonation alerts | Free. |

---

## 4. Data we generate ourselves

The community layer has no public dataset — it *is* the product's proprietary asset, and the reason the moat compounds.

- `reports` — user-submitted fraud reports with structured evidence
- `reviews` — multi-dimension recruiter ratings from verified interactions
- `verifications` — every score ever computed, immutable, with full signal breakdown

This is what makes VeriHire defensible: the models are reproducible by anyone, the accumulated verified community graph is not.

---

## 5. Directory layout & pipeline

```
services/ml/
├─ data/
│  ├─ raw/          # untouched downloads — gitignored
│  ├─ interim/      # cleaned, deduped
│  └─ processed/    # train.parquet / val.parquet / test.parquet — split BEFORE any fitting
├─ artifacts/v1/    # vectorizer.joblib, model.joblib, threshold.json, metrics.json
└─ src/
   ├─ ingest.py     # download + validate schema + checksum
   ├─ features.py   # TF-IDF, embeddings, engineered risk features
   ├─ train.py
   ├─ evaluate.py
   └─ explain.py
```

**Rules:**
- Raw data is never committed. `make ml.data` downloads and verifies a checksum.
- Split first, fit second. Any vectorizer or scaler fitted on the full dataset is leakage and invalidates the metrics.
- Fixed random seed everywhere; `make ml.train` must reproduce the reported numbers exactly.
- Every artifact directory carries a `metrics.json` and a `datacard.md` recording source, date, row counts and split hashes.

---

## 6. Mapping datasets to Trust Score sub-scores

| Sub-score | Weight | Data source |
|---|---|---|
| `identity` | 20% | Live: DNS, email domain match, profile completeness, account age |
| `company_legitimacy` | 25% | Live: RDAP, MX/SPF/DMARC, TLS, OpenCorporates, MCA |
| `content_risk` | 30% | **EMSCAD model** + hand-crafted risk phrase families |
| `link_safety` | 10% | **PhiUSIIL model** + Safe Browsing + redirect analysis |
| `community_signal` | 15% | Our own `reports` and `reviews` tables |

---

## 7. Ethics and honesty

- A Trust Score is **advisory**, never a determination of guilt. The UI must say so, in plain language, on every verdict page.
- False accusations cause real harm to real recruiters. Tune the operating threshold for **high precision**, and always provide an appeals path for a reported party.
- Retain report evidence only as long as it is needed for moderation, then purge on a schedule.
- Do not scrape anything a site's `robots.txt` disallows, and rate-limit everything.
- Publish the methodology (`docs/scoring.md`) and the limitations (`docs/limitations.md`). A trust product that is opaque about its own reasoning has already lost the argument.
