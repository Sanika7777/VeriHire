# API overview

The OpenAPI schema (served live at `GET /openapi.json`, browsable at
`GET /docs`) is the single source of truth for request/response shapes —
this file is a map of what exists and why, not a duplicate reference that
can drift out of sync with the code.

Base path: `/api/v1`. Conventions: plural resource nouns, `kebab-case`
paths, `snake_case` JSON bodies, cursor pagination (`?cursor=&limit=`
returning `{data, next_cursor, has_more}`), RFC 9457 Problem Details on
every error. See `CLAUDE.md` §6 for the full contract.

## Auth (`/auth`)

Register, login, refresh (rotating, HTTP-only cookie), logout, `/me`,
`DELETE /me` (real account deletion), `GET /me/export` (GDPR data export),
email verification, password reset, Google OAuth (Authorization Code +
PKCE) via `/auth/oauth/google/start` and `/auth/oauth/google/callback`.

## Entities

- `/companies`, `/recruiters`, `/postings` — CRUD + cursor-paginated lists.
  Create requires auth; update/delete require moderator/admin.
- `/companies/{id}/claim` + `/companies/claims/{id}/verify-dns` — the
  company-portal claim flow (email-domain match auto-approves; DNS TXT
  requires a real record and is verified live against DNS).

## Search & resolve

- `GET /search?q=&type=&band=&cursor=` — trigram fuzzy match across
  companies/recruiters/postings, joined against each subject's latest
  Trust Score, with facet counts. Ranked by similarity with keyset
  pagination.
- `POST /resolve` — the "paste a link" front door. Classifies a URL
  (LinkedIn profile → recruiter, bare domain → company, otherwise → job
  posting), finds an existing match or creates a stub entity. SSRF-guarded
  and robots.txt-respecting when it fetches the page to get a display name.

## Verification (the Trust Score engine)

- `POST /verifications` → `202 { verification_id, status }`. Computation
  runs asynchronously on an ARQ worker.
- `GET /verifications/{id}` — current state (score, band, sub_scores,
  signals, or `error_detail` if failed).
- `GET /verifications/{id}/stream` — Server-Sent Events; one `stage` event
  per status transition (`pending → resolving → scoring → done`).
- `GET /verifications/latest` / `/verifications/history` — by
  `subject_type` + `subject_id`.

Scores are immutable — every computation is a new row.

## Reports & reviews

- `POST /reports` — idempotency-key-aware (`Idempotency-Key` header),
  duplicate detection (same reporter + subject within 24h).
- `POST /reviews`, `POST /reviews/{id}/vote` — one vote per user per
  review, four rating dimensions.

## Admin (`moderator`/`admin` only)

- `/admin/reports` — triage queue; `/confirm` and `/reject` both require a
  `reason` and write an audit log row. Confirming enqueues a fresh
  verification (the hard-cap-at-25 override takes effect there).
- `/admin/dashboard` — live counts, band distribution, top-reported
  subjects.
- `/admin/scoring-config` (GET), `/admin/scoring-config/preview` (POST),
  `/admin/scoring-config` (PUT, admin-only) — weight management with a
  before-you-publish impact preview.
- `/admin/companies/merge`, `/admin/recruiters/merge` — duplicate
  resolution; reassigns child postings/recruiters before soft-deleting the
  source.

## Observability

- `GET /health` — liveness.
- `GET /ready` — dependency check (Postgres, Redis).
- `GET /metrics` (staff-authenticated) — basic live counters.

## Auth boundary summary

| Route prefix | Anonymous | Seeker/Employer | Moderator/Admin |
|---|---|---|---|
| `/search`, `/companies` (GET), `/resolve` | ✅ | ✅ | ✅ |
| `/companies` (POST), `/reports`, `/reviews`, `/verifications` (POST) | ❌ | ✅ | ✅ |
| `/companies/{id}` (PATCH/DELETE), `/admin/*` | ❌ | ❌ | ✅ |
| `/admin/scoring-config` (PUT) | ❌ | ❌ | admin only |
