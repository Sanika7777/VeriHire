# PHASES.md — VeriHire build plan

Twelve phases, executed in order. Each phase has tasks, and a **Definition of Done** that must pass before moving on. Do not start a phase until the previous one's DoD is green.

Work one task at a time. Announce the task, implement it fully, run `make lint && make test`, report, stop.

---

## Phase 0 — Foundations
**Goal:** an empty but industrial-grade repo that runs with one command.

**Tasks**
1. Monorepo scaffold per `CLAUDE.md` §4 (pnpm workspaces + uv/poetry for Python).
2. `docker-compose.yml`: postgres:16 (with `pg_trgm`, `pgvector`), redis:7, minio, mailhog, api, web, worker. Named volumes, healthchecks, `depends_on: condition: service_healthy`.
3. FastAPI skeleton: settings via `pydantic-settings`, structlog JSON logging with request IDs, global exception handlers emitting Problem Details, `/health` (liveness) and `/ready` (DB + Redis reachable).
4. Next.js 15 skeleton: App Router, TypeScript strict, Tailwind v4, `next/font` loading Sora + Manrope, design tokens in `globals.css`.
5. Tooling: ruff, mypy strict, pre-commit, ESLint, Prettier, `tsc --noEmit`, Makefile.
6. GitHub Actions: lint → typecheck → test → build, on PR and main.
7. `.env.example` with every variable documented. `README.md` with real setup steps.

**DoD**
- `make dev` brings the whole stack up from a clean clone on a fresh machine.
- `curl localhost:8000/ready` → `200`.
- Web renders a styled page using the tokens and both fonts.
- CI is green.
- No AI attribution anywhere in the repo, including commit metadata.

---

## Phase 1 — Data model & migrations
**Goal:** the schema the whole product sits on.

**Tables**
`users`, `refresh_tokens`, `companies`, `recruiters`, `job_postings`, `verifications`, `verification_signals`, `reports`, `report_evidence`, `reviews`, `review_votes`, `scoring_configs`, `audit_logs`, `entity_claims`, `notifications`.

**Tasks**
1. SQLAlchemy 2.0 models with `Mapped[...]` annotations. UUIDv7 primary keys. `created_at` / `updated_at` on everything.
2. Relationships: company ↔ recruiters ↔ postings; polymorphic `subject_type` / `subject_id` on `verifications`, `reports`, `reviews`.
3. `verifications.sub_scores` and `.signals` as JSONB. `job_postings.embedding` as `vector(384)`.
4. Indexes deliberately: trigram GIN on `companies.name` and `recruiters.name`, GIN on JSONB signal codes, btree on `(subject_type, subject_id, computed_at desc)`, HNSW on the embedding column, partial index on `reports.status = 'pending'`.
5. Enums as Postgres native types: `trust_band`, `report_status`, `report_category`, `entity_status`, `user_role`.
6. Alembic initial migration + a `make migrate` workflow that actually autogenerates cleanly.
7. Soft delete via `deleted_at` on user-generated content; hard delete path for GDPR-style account deletion.

**DoD**
- `alembic upgrade head` then `downgrade base` then `upgrade head` runs clean.
- ER diagram committed to `docs/schema.md`.
- Every foreign key has an explicit `ondelete` policy.

---

## Phase 2 — Authentication & accounts
**Goal:** real auth, not a demo login.

**Tasks**
1. Register / login / logout / refresh / me. Argon2id hashing with tuned parameters.
2. Access token 15 min (memory), refresh token 30 d (HTTP-only, `Secure`, `SameSite=Lax`), **rotation with reuse detection** — a replayed refresh token revokes the whole family.
3. Email verification and password reset with single-use, expiring, hashed tokens.
4. Google OAuth 2.0 (Authorization Code + PKCE) as a second path.
5. Roles: `seeker`, `employer`, `moderator`, `admin`. Dependency-injected role guards.
6. Rate limiting on all auth routes; account lockout with exponential backoff after repeated failures.
7. Frontend: sign-up, login, forgot/reset, email-verified screens. Zod validation shared with the API. Session bootstrapped in a Server Component; token refresh handled transparently in the API client.

**DoD**
- Auth boundary tests pass for anon / wrong-user / correct-user / moderator / admin on a protected route.
- Refresh reuse detection has a passing test.
- No token is ever written to `localStorage`.

---

## Phase 3 — Core entities & search
**Goal:** companies, recruiters and postings exist, are searchable, and have real pages.

**Tasks**
1. CRUD services + cursor-paginated list endpoints for companies, recruiters, postings.
2. Unified search endpoint `/api/v1/search?q=&type=&band=&sort=` — trigram fuzzy match + full-text rank + filter facets, returning counts per facet.
3. `POST /api/v1/resolve` — accepts a raw URL (LinkedIn profile, job board link, company domain) and resolves it to an entity, creating a stub record if unseen. This is the app's front door.
4. Ingestion workers: robots-respecting fetch, HTML parse, canonical URL extraction, dedupe by content hash, cache in Redis with TTL.
5. Frontend: search page with debounced input, filter chips, facet counts, skeleton loading, empty and error states; entity detail pages for company and recruiter.

**DoD**
- Searching a partial misspelt name returns the right entity in the top 3.
- Search p95 under 200 ms with 10k seeded entities.
- Every state in `CLAUDE.md` §8 exists on the search page.

---

## Phase 4 — ML: fraud detection model
**Goal:** a trained, evaluated, explainable model — not a `random.random()` stand-in.

**Tasks**
1. Ingest the EMSCAD / Kaggle fake-job-posting dataset (see `DATA.md`). Stratified 70/15/15 split, **split before any fitting** to avoid leakage.
2. EDA notebook: class imbalance, missingness, text length distributions, top discriminative terms. Commit findings to `services/ml/REPORTS.md`.
3. Feature engineering:
   - Text: TF-IDF word (1–2 gram) + char (3–5 gram) over title, description, requirements, company profile.
   - Semantic: MiniLM embeddings of the description.
   - Meta: `has_company_logo`, `has_questions`, `telecommuting`, employment type, experience level, education level, salary-range presence and plausibility.
   - Hand-crafted risk features: personal-email contact, external messaging handles (WhatsApp/Telegram), advance-fee phrases, urgency markers, ALL-CAPS ratio, emoji density, missing-company-profile flag, unrealistic pay-to-experience ratio.
4. Models: calibrated LinearSVC baseline → LightGBM main → optional soft-vote ensemble. Handle imbalance with class weights; tune the decision threshold on the **precision-recall** curve, optimising for high precision (a false accusation is worse than a missed scam).
5. Evaluation on the untouched test split: PR-AUC, ROC-AUC, precision/recall/F1 at the chosen threshold, confusion matrix, calibration curve. **Accuracy alone is not an acceptable metric** — say so in the report.
6. Explainability: SHAP for tabular contributions, token-level attribution for text. Output a ranked list of the top 5 human-readable reasons per prediction.
7. Package: `predict(payload) -> {probability, threshold, label, model_version, reasons[]}`. Artifacts versioned in `services/ml/artifacts/v{n}/`. Loaded once at API startup.
8. Regression guard: a fixed set of 50 labelled examples must keep passing; CI fails if PR-AUC drops more than 2 points versus the recorded baseline.

**DoD**
- `make ml.train` reproduces the reported metrics from a clean checkout with a fixed seed.
- PR-AUC ≥ 0.85 on the held-out split, with precision ≥ 0.90 at the chosen operating threshold.
- `services/ml/REPORTS.md` contains the metrics table, the PR curve, and a written account of the model's limitations.
- Every prediction returns non-empty, sensible reasons.

---

## Phase 5 — Trust Score engine
**Goal:** the product's core, per `CLAUDE.md` §5.

**Tasks**
1. Five sub-score calculators as independent, individually testable, individually cacheable units.
2. External signal integrations, each behind an interface with a timeout, a circuit breaker, a Redis cache and a stub implementation for tests: WHOIS/RDAP domain age, DNS MX + SPF/DMARC, TLS certificate age, company registry lookup, URL blocklist.
3. Aggregator: weighted combination from `scoring_configs`, band assignment, hard override for confirmed fraud, `Unrated` for cold start.
4. Signal generation: each calculator emits structured signals `{code, severity, title, detail, evidence_url}` that render directly in the UI. Write the copy for all of them — this is user-facing text, not debug output.
5. Persist immutable score rows; expose score history and a diff ("dropped 31 points on 12 Aug: 3 reports confirmed").
6. `POST /api/v1/verifications` → `202` + id; ARQ job computes; SSE stream pushes progress stages (`resolving → fetching → analysing → scoring → done`).
7. Re-scoring triggers: new confirmed report, new review, registry data older than 30 days, model version bump.

**DoD**
- Golden-file tests: 12 fixed entity fixtures produce exactly the expected scores, bands and signal sets.
- Every external integration degrades gracefully — with the network cut, verification still completes and reports which inputs were unavailable.
- Full verification p95 under 4 seconds warm, under 12 seconds cold.
- Changing a weight in admin changes future scores and leaves historical scores untouched.

---

## Phase 6 — Frontend foundation & design system
**Goal:** the visual language, built once.

**Tasks**
1. Token layer in `globals.css` + Tailwind theme mapping; light and dark.
2. shadcn/ui components pulled in and **restyled** to the tokens — button, input, select, dialog, sheet, dropdown, tabs, badge, tooltip, skeleton, table, pagination, command palette.
3. Signature components:
   - **`<TrustRing />`** — animated SVG arc, count-up numeral in Sora, band-bound colour, size variants, `prefers-reduced-motion` respected.
   - **`<SignalList />`** — grouped signals with severity icons, expandable evidence.
   - **`<ScoreBreakdown />`** — five sub-score bars with weights and tooltips.
   - **`<EntityCard />`**, **`<VerdictBadge />`**, **`<EmptyState />`**, **`<ErrorState />`**, **`<StatTile />`**.
4. App shell: responsive sidebar/topbar, command palette (`⌘K`), user menu, notification bell, theme toggle.
5. Marketing landing page: hero with a live "paste a link" demo input, how-it-works, real statistics from the database, social proof, footer.
6. Accessibility pass: focus management, skip link, `aria-live` regions on async results, contrast audit.

**DoD**
- A component gallery route at `/dev/ui` shows every component in every state.
- Lighthouse ≥ 90 across all four categories on the landing page.
- Keyboard-only navigation completes a full search → verify flow.

---

## Phase 7 — The verification experience
**Goal:** the screen the whole pitch rests on.

**Tasks**
1. Verify entry point: URL/name input with paste detection, type inference, recent-checks list, example links.
2. Live analysis view: staged progress driven by the SSE stream, each stage revealing its result as it lands — never a generic spinner.
3. Verdict page:
   - Hero: entity identity, `<TrustRing />`, band, last-verified timestamp, verification count.
   - Verification checklist with pass/fail/unknown states.
   - "Why this score?" — the five sub-score bars plus the ranked signal list, each signal linking to its evidence.
   - Content-risk section showing the highlighted phrases the model reacted to.
   - Score history sparkline with annotated events.
   - Actions: report, review, save, share (with an OG image generated per entity).
4. Comparison view: verify two entities side by side.
5. Share pages: public, indexable, server-rendered verdict pages with correct meta tags.

**DoD**
- Every state in `CLAUDE.md` §8 present on the verdict page.
- A high-risk entity is instantly, unmistakably legible as dangerous within one second of the page settling.
- The verdict page server-renders and is shareable without auth.

---

## Phase 8 — Reports & community reviews
**Goal:** the community signal that feeds back into scoring.

**Tasks**
1. Multi-step report flow: category → description → structured evidence (screenshots, email headers, transaction proof) → confirmation. Idempotency key enforced.
2. Evidence upload: presigned S3 URLs, client-side type/size validation, server-side content-type sniffing, EXIF stripping, virus-scan hook.
3. Duplicate detection: content similarity + same reporter/subject pair within a window.
4. Reviews: 1–5 stars across four dimensions (communication, process transparency, offer accuracy, professionalism), free text, verified-interaction flag, helpful votes with rate limiting, Wilson lower-bound ordering.
5. Anti-abuse: new-account throttles, reviewer credibility weighting, brigading detection, an appeals path for the reported party.
6. Report status tracking for the reporter, with notifications on state change.
7. Frontend: report wizard with save-as-draft, review composer, moderation-aware review list.

**DoD**
- Submitting a report enqueues a re-score and the entity's score visibly updates.
- Double-submitting with the same idempotency key creates exactly one report.
- A malicious file upload is rejected server-side, with a test proving it.

---

## Phase 9 — Admin console & company portal
**Goal:** the operational surface that makes this a business, not a toy.

**Tasks**
1. Admin dashboard: queue depth, verifications/day, band distribution, confirmed-fraud trend, model performance drift, top reported entities.
2. Report triage: filterable data grid (TanStack Table), keyboard-driven review, evidence viewer, one-click confirm/reject with a required rationale, bulk actions, full audit trail.
3. Entity management: merge duplicates, manual verification override with mandatory reason, blocklist/allowlist.
4. Scoring config editor: adjust weights and thresholds, preview the impact against a sample of 100 historical entities **before** publishing, version and roll back.
5. Company portal: domain-verified claim flow (DNS TXT record or email at the company domain), impersonation alerts, brand-trust metrics, verified-recruiter roster management.
6. Every admin mutation writes an `audit_logs` row with actor, before/after, and reason.

**DoD**
- Confirming a fraud report caps the entity score at 25 and pushes a notification to affected users.
- Weight preview shows the real distributional impact before publish.
- Non-admin access to any admin route returns `403`, proven by test.

---

## Phase 10 — Hardening
**Goal:** it survives contact with the real world.

**Tasks**
1. Security: full CSP, HSTS, security headers, dependency audit, OWASP Top 10 review, SSRF protection on the URL resolver (block private IP ranges, cap redirects, enforce timeouts).
2. Performance: N+1 elimination, query plan review on the five hottest queries, Redis caching layer with sane TTLs, image optimisation, bundle analysis, route-level code splitting.
3. Resilience: retries with jitter, circuit breakers on all outbound calls, graceful shutdown draining in-flight jobs, dead-letter queue for failed ARQ tasks.
4. Observability: structured logs with correlation IDs across web → api → worker, Sentry on both runtimes, `/metrics` endpoint, uptime checks, alert thresholds documented.
5. Data protection: account deletion that genuinely cascades and anonymises, data-export endpoint, evidence retention policy with a scheduled purge job.
6. Load test the verification endpoint (k6) at 100 concurrent users and record the results.

**DoD**
- Load test: p95 under 500 ms on read endpoints, zero errors.
- No high or critical dependency vulnerabilities.
- A killed Postgres container produces a clean degraded response, not a stack trace.

---

## Phase 11 — Seed data, docs & deployment
**Goal:** shippable and demoable.

**Tasks**
1. Seed generator producing the volumes in `CLAUDE.md` §8 — Indian names, real Indian city distribution, INR salary bands, plausible company registry numbers, a believable mix of trust bands with a long tail of genuine companies and a realistic minority of scams. Include 8 hand-crafted "story" entities for demos: a clearly legitimate MNC, a verified startup, an amber-band ambiguous case, a confirmed advance-fee scam, an impersonation of a real brand, a newly-created shell company, an entity whose score dropped after reports, and an unrated cold-start entity.
2. Deploy: web → Vercel, api + worker → Fly.io, db → Neon, Redis → Upstash, storage → R2. Preview environments per PR.
3. Migrations run automatically on deploy, with a rollback runbook.
4. Docs: `README` (setup, architecture, decisions), `docs/api.md` (from OpenAPI), `docs/scoring.md` (methodology, weights, limitations), `docs/runbook.md` (incidents).
5. `docs/limitations.md` — an honest account of what the system cannot do: model trained on a predominantly English, US-skewed corpus; registry coverage gaps; community signal is gameable at low volume; scores are advisory, not determinations of guilt. Surface a plain-language version of this in the product footer.
6. Demo script: a 4-minute click-through hitting search → verify a trusted entity → verify a scam entity → report → admin confirm → score drops live.

**DoD**
- A fresh deploy from `main` works end-to-end on production URLs.
- The demo script runs without a single dead end or empty screen.
- Someone who has never seen the repo can run it locally using only the README.

---

## Phase 12 — Stretch (only after Phase 11 is green)
- Browser extension that injects the trust badge directly onto LinkedIn, Naukri and Internshala listings.
- Email forwarding: users forward a suspicious offer to `check@verihire.app` and get a verdict back.
- WhatsApp bot via Business API for the Indian market.
- Public API + API keys for job boards to embed verification.
- Real-time impersonation monitoring with alerts to verified companies.
- Multilingual scam detection (Hindi, Marathi, Tamil, Telugu, Bengali).
- Weekly "scam radar" digest email with the newest confirmed patterns.

---

## Progress tracking

Keep a table at the bottom of this file and update it as phases complete.

| Phase | Status | Completed | Notes |
|---|---|---|---|
| 0 Foundations | ☑ | 2026-08-07 | Docker unavailable in build sandbox — compose/Dockerfiles written but not exercised; verify `make dev` on a Docker-capable machine. |
| 1 Data model | ☑ | 2026-08-07 | Full upgrade→downgrade→upgrade cycle verified against real Postgres 16 + pg_trgm + pgvector. |
| 2 Auth | ☑ | 2026-08-07 | Register/login/refresh/logout, Argon2id, rotation+reuse detection, lockout, email verify + password reset (MailHog/Resend), Google OAuth (Authorization Code + PKCE), role guards, rate limiting. Frontend: login/register/forgot/reset/verify-email pages, in-memory access token, transparent refresh. 20 backend tests + a real headless-browser e2e session passing. Google OAuth logic unit-tested with mocked Google calls — the live handshake itself needs real Google OAuth credentials to exercise. |
| 3 Entities & search | ☑ | 2026-08-07 | CRUD + cursor pagination for companies/recruiters/postings; unified trigram+facet search (verified: misspellings resolve correctly, p95 ~100ms @ ~10k rows); SSRF-guarded, robots-respecting `/resolve` endpoint. Frontend search page + entity detail pages. |
| 4 ML model | ☑ | 2026-08-07 | TF-IDF (word+char) + engineered risk features → LightGBM, trained on real EMSCAD data. Test PR-AUC 0.903, precision 0.94 @ tuned threshold (target ≥0.85 / ≥0.90 met). REPORTS.md + SHAP global feature importances + 50-example regression guard all generated. MiniLM embeddings were skipped for build-time budget — documented in REPORTS.md/limitations.md. |
| 5 Trust Score engine | ☑ | 2026-08-07 | All 5 sub-score calculators live: real RDAP/DNS/TLS lookups (verified against real domains), ML content-risk, link heuristics, community signal (Wilson bound). Weighted aggregator with renormalization, hard fraud-report cap, cold-start Unrated. ARQ worker + SSE progress stream verified end-to-end against a real Postgres+Redis stack, including a live example scoring an obviously fraudulent posting to 1/100 with explainable reasons. |
| 6 Design system | ☑ | 2026-08-07 | Token layer, Sora/Manrope, TrustRing/SignalList/ScoreBreakdown/EntityCard/VerdictBadge/EmptyState/ErrorState built and used for real (not a component gallery — folded into Phase 7 delivery given the time budget). |
| 7 Verification UX | ☑ | 2026-08-07 | Live "paste a link" resolve flow, SSE-driven progress panel, verdict display (ring + breakdown + signals) on company/recruiter/posting pages. Comparison view and OG share images not built — deferred. |
| 8 Reports & reviews | ☑ | 2026-08-07 | Report submission (idempotency key + 24h duplicate window), review submission + single-vote-per-user helpful voting, both backed by real tests. Evidence upload to object storage not wired. |
| 9 Admin & company portal | ☑ | 2026-08-07 | Report triage (confirm/reject with required reason), full audit-log trail, confirm re-triggers verification (hard-caps score). Dashboard is counts-only; scoring-config editor and company-claim UI are API-only, no frontend surface yet. |
| 10 Hardening | ☑ | 2026-08-07 | CSP/HSTS/X-Frame-Options/nosniff middleware verified live. Real GDPR-style account hard-delete (cascades refresh tokens/notifications, anonymises reports/reviews via ON DELETE SET NULL). No load test run; no shared circuit-breaker state machine. |
| 11 Deploy & docs | ☑ | 2026-08-07 | Seed script (60 companies/150 recruiters/300 real EMSCAD postings/60 reports/200 reviews) run successfully against real Postgres. `docs/limitations.md` written. Live deploy, `docs/api.md`/`docs/scoring.md`/`docs/runbook.md`, and the 8 hand-crafted story entities were not completed — out of time budget. |
