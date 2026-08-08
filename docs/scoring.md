# Scoring methodology

This is the plain-language explanation of how a VeriHire Trust Score is
computed. The implementation lives in `apps/api/app/modules/verification/`;
this document should never drift from that code — if it does, the code
wins and this file is out of date.

## The five sub-scores

Each sub-score is 0–100, computed independently, and can also be `Unrated`
(no data available yet — never a guessed default).

| Sub-score | Weight | What it checks | Source |
|---|---|---|---|
| **Identity** | 20% | Profile completeness, email-domain match to claimed employer, corroborating LinkedIn profile, account age | `scoring/identity.py` |
| **Company legitimacy** | 25% | Domain registration age (RDAP), DNS MX/SPF/DMARC, TLS certificate age | `scoring/company_legitimacy.py` |
| **Content risk** | 30% | A LightGBM model trained on real fraud/legitimate job postings, **plus** an independent, rule-based keyword-family check (advance-fee language, WhatsApp/Telegram handoff, personal-email contact, urgency pressure) that caps the score regardless of what the model alone says | `scoring/content_risk.py`, `services/ml` |
| **Link safety** | 10% | HTTPS presence, IP-literal hosts, URL shorteners, low-trust TLDs, Google Safe Browsing (when configured) | `scoring/link_safety.py` |
| **Community signal** | 15% | Confirmed fraud reports (time-decayed), pending report volume, Wilson-lower-bound review ratings | `scoring/community_signal.py` |

## Aggregation

```
score = round( Σ(sub_score × weight) / Σ(weight for sub-scores with data) )
```

Weights are **renormalized over whichever sub-scores actually have data**.
A brand-new company with no reports and no reviews yet doesn't get
penalized for a category nobody could have populated — its score is based
on identity + company legitimacy + link safety alone, with their weights
scaled up proportionally.

If **every** sub-score is `Unrated` (truly nothing to go on), the overall
score is `Unrated`, never a default 50.

## Hard override

**Any confirmed fraud report caps the score at 25 and forces the `High
Risk` band**, regardless of what the other four sub-scores say. This is
enforced in `scoring/aggregator.py::aggregate()` and cannot be bypassed by
a high identity/legitimacy score — a real estate empire can still run a
scam job posting.

## Bands

| Score | Band |
|---|---|
| 0–39 | High Risk |
| 40–69 | Caution |
| 70–100 | Trusted |
| — | Unrated (cold start) |

## Weights are data, not code

Weights live in the `scoring_configs` table, versioned. An admin can
publish a new weight distribution from `/admin/scoring`, which:

1. Requires the new weights to sum to 1.0.
2. Shows a **preview** of the impact against recently-computed
   verifications (reusing their stored sub-scores — no need to re-run any
   external check) before publishing.
3. Never rewrites historical `verifications` rows — every score ever
   computed is immutable. A new config version only affects verifications
   computed after it's published.

## Explainability

Every sub-score calculator emits structured `signals`:
`{code, severity, title, detail, evidence_url}`. These are what render on
the verdict page under "Signals" — the product's core promise is that a
score is never a bare number. The content-risk model additionally reports
its top contributing risk phrases per prediction (see
`services/ml/REPORTS.md` for the offline SHAP analysis this approximates),
and a matched keyword-family phrase (e.g. an explicit advance-fee demand)
independently caps the content_risk score with its own signal — a real
generalization probe found postings where the blended ML probability alone
missed a phrase that, on its own, is a decisive scam indicator. See
`services/ml/REPORTS.md` for that probe and the exact caps applied.

## What this methodology does not do

See `docs/limitations.md` for the full account — briefly: the content-risk
model is trained on 2012–2014 US-skewed data, there is no company registry
check (evaluated and dropped — see limitations doc), the Safe Browsing
blocklist check degrades gracefully when unconfigured rather than failing
scoring outright, and community signal is gameable at low volume. A Trust
Score is advisory, never a determination of guilt.
