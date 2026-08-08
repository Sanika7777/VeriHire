# Limitations — read this before trusting a score

VeriHire's Trust Score is **advisory**. It is not a determination of guilt,
not a legal finding, and not a guarantee. Treat a low score as a reason to
look closer, not as proof of fraud — and treat a high score as one good
signal among several you should still apply your own judgement to.

## What the content-risk model actually knows

The fraud-detection model (`services/ml`) is trained on the EMSCAD dataset:
~17,880 job postings collected 2012–2014, predominantly English-language and
US-skewed. Concretely, that means:

- It will underperform on Indian regional postings, Hinglish or vernacular
  scam text, and any language pattern outside its training distribution.
- Scam techniques invented after ~2014 — Telegram "task scam" pyramids,
  crypto payment demands, deepfaked video interviews — are underrepresented
  or absent from what it learned.
- It is one of five Trust Score inputs (30% weight), never the sole basis
  for a verdict, and a confirmed human-reviewed fraud report always
  overrides it (score capped at 25 regardless of model output).

## What the other sub-scores can and can't see

- **Identity** and **company legitimacy** depend on data being present at
  all — a company with no domain on file gets `Unrated` on that dimension,
  not a default middling score. Absence of evidence is not evidence of
  fraud, and we don't pretend otherwise.
- **Company registry matching is not implemented.** We evaluated
  OpenCorporates and dropped it — it's a paid API with weak coverage of
  Indian jurisdictions, which is our primary market. `company_legitimacy`
  is based on WHOIS/RDAP domain age, DNS (MX/SPF/DMARC), and TLS
  certificate checks only.
- **Safe Browsing** blocklist checks require an API key. Without it, that
  check reports itself as "unavailable" rather than silently passing — but
  it does mean a deployment without that key configured is working with
  less signal than the full design calls for.
- **Community signal** is entirely user-submitted and is gameable at low
  report/review volume — a handful of coordinated fake reports or reviews
  can currently move a score more than they should. Reviewer credibility
  weighting and brigading detection are not yet implemented.

## Coverage gaps

- No company registry check at all (see above) — a registration-authority
  cross-check like MCA/data.gov.in for Indian entities remains a possible
  future addition if a suitable free/low-cost source is found.
- WHOIS/RDAP domain-age data is unavailable for some registrars and some
  ccTLDs.
- The URL-safety sub-score currently combines lexical heuristics with
  Safe Browsing; it does not yet run the dedicated PhiUSIIL-trained
  phishing-URL model described in `DATA.md` §2 — that model was not
  trained as part of this build pass.

## What we have not built yet

This build pass implemented Phases 0–11 of `PHASES.md` at a working-MVP
depth, not full production polish. In particular:

- No live circuit-breaker state machine on external integrations — each
  call has its own timeout and degrades gracefully per-request, but there
  is no shared "stop calling a failing dependency for N seconds" breaker
  yet (Phase 10 in the plan, only partially realized).
- Evidence upload (screenshots, email headers) for reports is not wired to
  object storage yet — reports are text-only right now.
- The dedicated admin scoring-config editor UI, company-portal claim flow
  UI, and comparison/share views described in Phases 7 and 9 are backed by
  working APIs but do not yet have full frontend surfaces.
- Load testing (k6) against the verification endpoint has not been run in
  this environment.

## Our commitment

We will keep publishing this document as the system changes. If you find a
gap this page doesn't mention, that's a bug in our honesty, not just our
code — please report it.
