# Demo script (≈4 minutes)

A click-through of the product using the eight hand-crafted "story" entities
created by `make seed` (`apps/api/app/db/seed.py::seed_story_entities`), so
every run of this script produces the same outcomes. Run `make seed` fresh
before demoing if you want the exact scores below — reports/reviews from the
random seed data don't affect these entities, but a stale database might be
missing them if seeded before this function existed.

Sign in as `admin@verihire.app` / `AdminPassword123!` when a step calls for
the admin console; otherwise stay signed out or use a seeker account.

## 1. Search and the trust score (60s)

1. On the home page, search **"Meridian Software"**.
2. Open **Meridian Software Solutions Pvt Ltd** — a 20-year-old IT services
   company. Its Trust Score ring animates to **94, Trusted (green)**.
3. Point out the sub-score breakdown (identity, company legitimacy, content
   risk, link safety, community signal) and that every one of them is
   backed by a plain-language signal, not a bare number — e.g. "Domain
   registered 20 years ago."

## 2. An ambiguous, amber case (30s)

1. Search **"Bluepeak Consulting"**.
2. Its score is **54, Caution (amber)** — call out that this is the honest
   middle: no SPF/DMARC on its mail domain (inconclusive on its own for a
   small consultancy), one salary outlier, mixed reviews. Nothing here
   proves fraud, and the product doesn't pretend otherwise.

## 3. A confirmed scam, hard-capped (45s)

1. Search **"GlobalCareer Overseas"**.
2. Its score is **25, High Risk (red)**, with a visible banner: *"Capped at
   25 due to a confirmed fraud report."*
3. Open the signals list — advance-fee language detected in the posting
   text, plus the confirmed report itself (an upfront "visa processing fee"
   demand). This is the hard-override rule from CLAUDE.md §5: a confirmed
   fraud report caps the score regardless of what the other four sub-scores
   say.

## 4. Brand impersonation (30s)

1. Search **"Tata Consultancy Servicess Careers"** (note the deliberate
   misspelling — "Servicess").
2. Score **18, High Risk**. The domain `tcs-careers-hiring.com` is flagged
   as a lookalike domain impersonating a well-known company's name, and was
   registered only days before scoring — the opposite profile of a
   legitimate multinational's decades-old domain.

## 5. Submitting a report and watching a score drop live (60s)

1. Sign in as a seeker (or register a new account inline).
2. Search **"Rapid Corp Solutions"** — a newly registered shell company,
   currently **42, Caution**, with `community_signal` excluded entirely
   (no reports or reviews yet, so its weight is renormalized across the
   other four sub-scores rather than penalizing the entity for a category
   nobody could have populated).
3. Submit a report against it (any category, e.g. "Fake job posting").
4. Switch to the admin console (`/admin/reports`) as `admin@verihire.app`.
5. Find the new pending report and **Confirm** it with a reason.
6. Confirming enqueues a fresh verification. Watch `GET
   /verifications/{id}/stream` (or just refresh the entity page after a
   few seconds) — the score drops and the band flips to High Risk, capped
   at 25, because a confirmed report now exists.
7. This mirrors exactly what already happened historically to **Bright
   Horizon Careers** — its first verification scored 79/Trusted three weeks
   ago; after a confirmed "training kit" interview-scam report two days
   ago, its current score is 25/High Risk. Its score history graph on the
   entity page shows both points, since scores are immutable and every
   recomputation is a new row, never an edit.

## 6. Cold start — no invented confidence (15s)

1. Search **"Sundari Textiles Exports"**.
2. It shows **Unrated**, not a default 50 — this entity has never been
   verified. Trigger a verification from the page to show the `pending →
   resolving → scoring → done` progress stream, then land on whatever score
   the live calculators produce (this one isn't scripted, since it depends
   on real outbound RDAP/DNS/link-safety calls at demo time).

## Story entity reference

| Entity | Intended state |
|---|---|
| Meridian Software Solutions Pvt Ltd | 94, Trusted — clearly legitimate MNC |
| NimbusStack Labs | 81, Trusted — verified startup (claimed via email domain) |
| Bluepeak Consulting Services | 54, Caution — genuinely ambiguous |
| GlobalCareer Overseas Placements | 25, High Risk — confirmed advance-fee scam, hard-capped |
| Tata Consultancy Servicess Careers | 18, High Risk — brand impersonation via lookalike domain |
| Rapid Corp Solutions | 42, Caution — newly created shell company |
| Bright Horizon Careers | 79 → 25 — score dropped after a confirmed report |
| Sundari Textiles Exports | Unrated — cold start, never verified |
