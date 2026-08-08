# CLAUDE.md — VeriHire

Operating instructions for any coding agent working in this repository. Read this file fully before writing code. It overrides general habits and defaults.

---

## 1. What we are building

**VeriHire** is a production web application that lets job seekers verify recruiters, companies and job postings *before* they apply, and lets the community report recruitment fraud.

A user pastes a job link, a recruiter profile URL, or a company name. The system returns a **Trust Score (0–100)** with a full, explainable breakdown: identity verification, company legitimacy, content-level fraud probability from a trained ML model, link/domain safety, and aggregated community signal. Every score is auditable — we always show *why*.

Three surfaces, one codebase:

| Surface | Users | Purpose |
|---|---|---|
| **Job seeker app** | Students, early-career candidates | Search, verify, read reports, submit reports, review recruiters |
| **Admin console** | Internal trust & safety team | Triage reports, confirm/reject fraud, manage entity records, tune score weights |
| **Company portal** | Employers / HR teams | Claim and verify a company, monitor impersonation attempts, see brand-trust metrics |

**This is not a prototype, a demo, or a college submission.** It is built and reviewed as if real users depend on it. See §9 for the standard.

---

## 2. Absolute rules

1. **No AI attribution anywhere.** Never write "Generated with", "Built with an AI assistant", `Co-Authored-By:` trailers, "AI-generated" comments, or any similar marker in code, commits, PR descriptions, README files, UI copy, footers, meta tags, or docs. Commits are authored by the repo owner only. This is non-negotiable.
2. **No placeholder content in committed code.** No `lorem ipsum`, no `TODO: add real copy`, no `console.log("here")`, no `<div>Coming soon</div>` shipped to a route a user can reach.
3. **No secrets in the repo.** Everything through `.env`, with `.env.example` kept current. Never commit a real key, even in a test fixture.
4. **No mock data behind a real API route.** If an endpoint exists, it queries the database. Seed data lives in `seeds/`, is clearly separated, and is realistic (§8).
5. **Never claim a task is done without running it.** Run the tests, run the type checker, hit the endpoint. If it wasn't executed, it isn't done.
6. **Ask before destructive operations** — dropping tables, rewriting migrations that have already been applied, force-pushing, deleting directories.
7. **Every ML prediction that reaches a user must be explainable.** A raw probability with no reasons is not shippable.

---

## 3. Tech stack

Chosen for production quality, not for novelty. Do not swap any of these without being asked.

### Frontend — `apps/web`
| Concern | Choice |
|---|---|
| Framework | **Next.js 15** (App Router, React Server Components, TypeScript strict) |
| Styling | **Tailwind CSS v4** with a token layer in `globals.css` |
| Components | **shadcn/ui** (Radix primitives), owned in-repo under `components/ui`, restyled to our tokens — never left at defaults |
| Data fetching | **TanStack Query v5** for client state; RSC + `fetch` for server data |
| Forms | **react-hook-form** + **Zod** resolvers, sharing schemas with the API contract |
| Motion | **Motion** (`motion/react`) — restrained, purposeful only |
| Charts | **Recharts**, restyled to our tokens |
| Icons | **Lucide** — one set, no mixing |
| Tables | **TanStack Table** for admin data grids |
| Toasts | **Sonner** |
| Auth client | HTTP-only refresh cookie + in-memory access token |

### Backend — `apps/api`
| Concern | Choice |
|---|---|
| Framework | **FastAPI** (Python 3.12), fully async |
| ORM | **SQLAlchemy 2.0** async + **Alembic** migrations |
| Validation | **Pydantic v2** — separate `Create` / `Update` / `Read` schemas, never expose ORM models |
| Database | **PostgreSQL 16** + `pg_trgm` (fuzzy search) + `pgvector` (semantic similarity) + JSONB for score breakdowns |
| Cache / rate limit | **Redis 7** |
| Background jobs | **ARQ** (Redis-backed async workers) for scraping, re-scoring, digest emails |
| Auth | JWT access (15 min) + rotating refresh (30 d, HTTP-only cookie), **Argon2id** hashing, optional Google OAuth |
| Storage | S3-compatible (Cloudflare R2 / MinIO local) for report evidence uploads |
| Email | Resend (or SMTP in dev via MailHog) |
| Logging | **structlog** JSON, request-scoped correlation IDs |
| Errors | **Sentry** |

### ML — `services/ml`
| Concern | Choice |
|---|---|
| Baseline | TF-IDF (word + char n-grams) → calibrated **LinearSVC** |
| Main model | **LightGBM** over engineered + embedding features |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Imbalance | class weights + threshold tuning on PR curve (**not** blind SMOTE) |
| Explanations | **SHAP** for tabular, token attribution for text |
| Serving | model artifacts via joblib, loaded once at API startup; `/v1/ml/health` reports `model_version` |
| Tracking | MLflow local runs; metrics committed to `services/ml/REPORTS.md` |

### Infra & tooling
- **Docker Compose** for local dev (api, web, postgres, redis, minio, mailhog)
- **GitHub Actions**: lint → typecheck → test → build on every PR
- **Ruff** + **mypy (strict)** + **pre-commit** (Python); **ESLint** + **Prettier** + `tsc --noEmit` (TS)
- **pytest** + `pytest-asyncio` + `httpx.AsyncClient` + factory-boy (API); **Vitest** + **Playwright** (web)
- Deploy: web → Vercel, api + worker → Fly.io/Render, db → Neon, cache → Upstash

---

## 4. Repository layout

```
verihire/
├─ apps/
│  ├─ web/                    # Next.js 15
│  │  ├─ app/
│  │  │  ├─ (marketing)/      # landing, pricing, about
│  │  │  ├─ (app)/            # authed job-seeker product
│  │  │  ├─ (admin)/          # trust & safety console
│  │  │  └─ api/              # BFF route handlers only
│  │  ├─ components/{ui,layout,verification,reports,charts}
│  │  ├─ lib/{api-client,auth,format,hooks}
│  │  └─ styles/globals.css   # design tokens
│  └─ api/
│     ├─ app/
│     │  ├─ core/             # config, security, deps, logging, errors
│     │  ├─ db/               # session, base, migrations
│     │  ├─ modules/
│     │  │  ├─ auth/ users/ recruiters/ companies/
│     │  │  ├─ postings/ verification/ reports/ reviews/ admin/
│     │  │  └─ each: router.py schemas.py service.py models.py repository.py
│     │  ├─ integrations/     # whois, dns, safe-browsing
│     │  └─ workers/          # ARQ tasks
│     └─ tests/
├─ services/ml/
│  ├─ data/ notebooks/ src/{features,train,evaluate,explain}/ artifacts/
├─ packages/shared/           # shared TS types generated from OpenAPI
├─ seeds/                     # realistic seed data
├─ docker-compose.yml
├─ CLAUDE.md   PHASES.md   DATA.md   README.md
```

**Module rule (API):** `router` handles HTTP only → `service` holds business logic → `repository` holds queries. A router must never contain a SQLAlchemy query. A service must never import `Request`.

---

## 5. The Trust Score engine — the heart of the product

Lives in `apps/api/app/modules/verification/`. Treat it as the most important code in the repo.

Five weighted sub-scores, each 0–100, each producing human-readable **signals**:

| Sub-score | Weight | Inputs |
|---|---|---|
| `identity` | 20% | Email domain matches claimed company, profile completeness, account age, verified contact, corroborating profiles |
| `company_legitimacy` | 25% | Domain age (WHOIS/RDAP), valid MX/SPF/DMARC records, HTTPS + cert age, careers page reachable, employee-count plausibility. (Company registry match was evaluated — OpenCorporates — and dropped: paid, and weak Indian-jurisdiction coverage anyway.) |
| `content_risk` | 30% | ML fraud probability over posting text + metadata (§3 ML), keyword risk families (advance fee, "no experience, high pay", personal-email contact, urgency pressure), salary-plausibility outlier check |
| `link_safety` | 10% | URL lexical model, TLD reputation, redirect chain depth, IP-literal hosts, shortener resolution, blocklist lookup |
| `community_signal` | 15% | Confirmed report count (time-decayed), report-to-view ratio, Wilson lower bound on review ratings, reviewer credibility weighting |

**Rules:**
- Weights live in a `scoring_config` table, are versioned, and are editable from admin — never hardcoded in a function body.
- Every score row persists: `score`, `band`, `sub_scores` (JSONB), `signals` (JSONB array of `{code, severity, title, detail, evidence_url}`), `model_version`, `config_version`, `computed_at`. Scores are **immutable**; recomputation writes a new row.
- Bands: `0–39 High Risk` (red), `40–69 Caution` (amber), `70–100 Trusted` (green).
- **Hard override:** any confirmed fraud report caps the score at 25 and forces the `High Risk` band, regardless of other sub-scores.
- Cold start: an entity with no data returns `Unrated`, never a default 50. Never invent confidence we don't have.
- Every score is recomputed asynchronously when new evidence arrives (new report, new review, domain re-check) via an ARQ job.

---

## 6. API conventions

- Base path `/api/v1`. Plural resource nouns. `kebab-case` in paths, `snake_case` in JSON bodies.
- Every list endpoint: cursor pagination (`?cursor=&limit=`), never offset. Return `{ data: [...], next_cursor, has_more }`.
- Errors follow RFC 9457 Problem Details:
  ```json
  { "type": "https://verihire.app/errors/validation", "title": "Validation failed",
    "status": 422, "detail": "…", "instance": "/api/v1/reports", "errors": [...] }
  ```
- Rate limits (Redis token bucket): anonymous verify `10/min`, authed verify `60/min`, report submission `5/hour`, auth endpoints `5/min` per IP.
- Idempotency: `Idempotency-Key` header required on POST `/reports` and `/verifications`.
- OpenAPI schema is the source of truth; regenerate `packages/shared` TS types on every contract change.
- Long-running verification returns `202` + a `verification_id`; the client polls `/verifications/{id}` or subscribes over SSE. Never block a request on scraping.

---

## 7. Design system — non-negotiable

Defined once in `apps/web/styles/globals.css` as CSS custom properties, consumed via Tailwind theme.

**Aesthetic direction: institutional trust with a signal layer.** Deep navy foundation, generous white space, restrained motion — and one loud verdict colour that appears *only* to communicate trust outcomes.

```css
--brand-navy-900: #0A1F44;   --brand-navy-700: #123163;
--brand-blue-600: #1D4ED8;   --brand-blue-100: #DBEAFE;
--brand-crimson: #D62828;
--signal-verified: #12A150;  --signal-caution: #F59E0B;  --signal-danger: #DC2626;
--ink-900: #0F172A;  --ink-500: #64748B;
--line-200: #E2E8F0; --surface-50: #F6F8FC; --surface-0: #FFFFFF;
```

- **Fonts:** `Sora` (headings, numerals, buttons) + `Manrope` (body). Loaded via `next/font`. Never Inter, Roboto, Poppins, or a system stack.
- **Signal colours are reserved for trust verdicts only.** Never for a primary CTA, never decorative. This restraint is what makes it read as a real security product.
- **Spacing scale:** `4 8 12 16 24 32 48 64` only. **Radii:** control `12`, card `16`, sheet `24`, pill `9999`.
- **Motion:** 150–300ms, `ease-out`. Animate the Trust Score ring filling and page-level enter transitions. Nothing else moves without a reason. Respect `prefers-reduced-motion`.
- **Dark mode** on every surface, driven by the same tokens.
- The Trust Score ring is the signature component: SVG `stroke-dasharray` arc, animated count-up, colour bound to the band, always accompanied by the plain-language reason list.

---

## 8. What "not a prototype" means — enforce on every page

A route is not complete until all of these exist:

- [ ] **Loading state** — content-shaped skeletons, not a spinner
- [ ] **Empty state** — illustration/icon, one sentence of guidance, a primary action
- [ ] **Error state** — retry affordance, plain-language message, never a raw stack trace
- [ ] **Partial/degraded state** — e.g. score computed but a WHOIS/RDAP lookup timed out; say so, don't hide it
- [ ] **Real content** — Indian names, INR amounts, plausible company names, realistic timestamps
- [ ] **Responsive** at 360 / 768 / 1280 / 1600
- [ ] **Keyboard reachable**, visible focus rings, correct heading order, `aria-live` on async results
- [ ] **Optimistic UI** for votes/helpful/dismiss, with rollback on failure
- [ ] **Pagination or virtualisation** for any list that can exceed 50 items
- [ ] Route-level `metadata` (title, description, OG image)
- [ ] Custom `not-found.tsx` and `error.tsx`

Global: real favicon and app icons, `robots.txt`, `sitemap.xml`, a working 404 and 500, Lighthouse ≥ 90 on Performance/Accessibility/Best Practices/SEO for public routes, and no console errors or warnings in a normal session.

**Seed volume:** at least 400 companies, 1,200 recruiters, 3,000 postings, 600 reports, 2,000 reviews, and 30 days of activity history. Sparse data is the fastest way for an app to look fake.

---

## 9. Code standards

**Python**
- Full type annotations. `mypy --strict` passes. No bare `except`. No `Any` without a comment justifying it.
- Async all the way down — no sync DB or HTTP calls in a request path.
- Services raise domain exceptions (`CompanyNotFound`, `DuplicateReport`); a single handler maps them to Problem Details. Routers do not build error responses.
- Docstrings on public service functions explain *why*, not *what*.

**TypeScript**
- `strict: true`, `noUncheckedIndexedAccess: true`. No `any`, no non-null `!` assertions.
- Server Components by default; `"use client"` only where interactivity requires it.
- Types for API payloads are generated from OpenAPI — never hand-written and never duplicated.
- One component per file. Props typed inline. No default exports except pages.

**Testing**
- Every service function: happy path + at least one failure path.
- Every endpoint: auth boundary test (anon / wrong user / correct user / admin).
- Scoring engine: golden-file tests — fixed inputs must produce exactly the expected score and signal set. These must never be edited to make a failing test pass without an explicit reason recorded in the commit.
- Playwright covers: sign up → verify a recruiter → view report → submit a report → admin confirms → score drops.
- Target ≥ 80% coverage on `modules/verification` and `modules/reports`.

**Git**
- Conventional Commits: `feat(verification): add company registry lookup`.
- One logical change per commit. No `wip`, no `fix stuff`.
- Branch per phase task: `feat/p4-ml-training-pipeline`.

**Security baseline**
- Argon2id passwords, rotating refresh tokens with reuse detection, CSRF protection on cookie-auth routes.
- Server-side authorisation on every mutation — never trust a client role claim.
- Parameterised queries only. Uploads: type + size validated, stored outside the web root, served via signed URLs.
- Strict CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy`.
- PII: report evidence is access-controlled and purgeable. Implement account deletion for real (cascade + anonymise), not as a flag.
- All outbound scraping respects `robots.txt`, sets a real User-Agent, and is rate-limited and cached.

---

## 10. Commands

```bash
make dev              # docker compose up: web, api, worker, postgres, redis, minio, mailhog
make api              # uvicorn app.main:app --reload
make web              # next dev --turbopack
make migrate m="msg"  # alembic revision --autogenerate
make upgrade          # alembic upgrade head
make seed             # load seeds/ into the dev database
make test             # pytest + vitest
make e2e              # playwright test
make lint             # ruff + mypy + eslint + tsc --noEmit
make ml.train         # train + evaluate + write artifacts/
make ml.eval          # evaluation report against the held-out split
```

Run `make lint && make test` before declaring any task complete.

---

## 11. Working style for the agent

- Work **one phase task at a time** from `PHASES.md`. State which task you're on, do it end-to-end, verify, then stop and report.
- Before writing a new file, search the repo for an existing pattern and follow it. Consistency beats cleverness.
- When a decision has a real trade-off (library choice, schema shape, threshold), state the options and your recommendation in one short paragraph, then proceed with the recommendation unless told otherwise.
- If a requirement in this file conflicts with what you're asked to do, flag the conflict rather than silently picking one.
- Prefer deleting code over adding flags. Prefer boring, obvious solutions.
- Do not build the whole app in one pass. Depth per phase, not breadth.
