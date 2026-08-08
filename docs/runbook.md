# Runbook

Operational notes for running and troubleshooting VeriHire. This documents
what the system actually does today, not an aspirational target — see
`docs/limitations.md` for gaps.

## Local development

```bash
cp .env.example .env
pnpm install && cd apps/api && uv sync && cd ../..
make dev       # docker compose: postgres, redis, minio, mailhog, api, web, worker
make upgrade   # apply migrations
make seed      # load realistic seed data (60 companies, 150 recruiters, 300 postings, ...)
```

If Docker isn't available in your environment, the individual pieces can
run directly: `make api`, `make web`, `make worker` — each needs Postgres
16 (with `pg_trgm` + `pgvector`) and Redis 7 reachable at the URLs in `.env`.

## Health checks

- `GET /health` — liveness, always 200 if the process is up.
- `GET /ready` — 200 with `{"status": "ok"|"degraded", "database": bool, "redis": bool}`.
  A "degraded" response with `database: false` or `redis: false` means the
  API is up but a dependency isn't reachable — check connection strings and
  that Postgres/Redis containers are healthy.
- `GET /metrics` (staff-authenticated) — live counts: total users, total
  verifications, pending reports.

## Common incidents

### Verifications stuck in `pending`

**Symptom**: `POST /verifications` returns 202, but `GET
/verifications/{id}` never leaves `pending`.

**Cause**: no ARQ worker is running to consume the job (`compute_verification`
was enqueued to Redis but nothing is listening), or the worker process
crashed.

**Fix**: `make worker` (or check the worker container's logs). Jobs persist
in Redis, so starting a worker after the fact will still process the
backlog — nothing is lost.

### A verification silently fails / `status: "failed"`

**Cause**: the subject was deleted or the wrong `subject_type` was passed
for a given `subject_id` (each subject_type looks the ID up in a different
table — a job-posting ID passed as `subject_type: "company"` will 404
inside the worker).

**Fix**: check `error_detail` on the verification row. This is a client
bug (wrong subject_type/id pairing), not an infra issue — no data is lost,
just re-request with the correct pairing.

### Refresh token "reuse detected" locking out a real user

**Cause**: this is refresh-token-rotation reuse detection working as
designed (CLAUDE.md §2) — it fires when a *revoked* (already-rotated)
refresh token is presented again. Usually caused by two tabs/devices racing
to refresh with the same stale cookie, or a genuinely stolen token.

**Fix**: the user needs to log in again — the whole token family was
revoked deliberately. If this happens frequently for legitimate users
without a stolen-token explanation, check for client-side code calling
`/auth/refresh` redundantly (e.g. two `useEffect`s both firing on mount).

### Content-risk sub-score always returns "model unavailable"

**Cause**: `services/ml/artifacts/v1/` doesn't exist — the model hasn't
been trained, or the API can't find it (see
`ml_content_risk._apps_api_root()` — it assumes a fixed directory depth
from `apps/api`).

**Fix**: `make ml.data && make ml.train` from `services/ml`, or verify
`ML_ARTIFACTS_DIR` in `.env` resolves correctly from `apps/api`.

### RDAP/DNS/registry checks all show "unavailable"

**Cause**: no outbound network access from the API process (sandboxed
environment), or `OPENCORPORATES_API_KEY` / `SAFE_BROWSING_API_KEY` aren't
set. This is expected, graceful degradation — verification still completes
with `Unrated` on the affected sub-score dimensions, per CLAUDE.md §5.

## Rotating the scoring config

Weight changes go through `/admin/scoring`: preview the impact against
recent verifications first, then publish. Publishing never touches
historical `verifications` rows — only future computations use the new
weights. There is no "undo" — to revert, publish the old weights again as
a new version.

## Rate limits

Redis-backed fixed-window limiters (`app/core/rate_limit.py`):

| Scope | Limit |
|---|---|
| Auth endpoints (login/register/password reset) | 5/min per IP |
| Report submission | 5/hour per IP |
| Resolve (`/resolve`) | 10/min per IP |

A `429` response includes a `Retry-After` header.

## Known gaps (see docs/limitations.md for full detail)

- No load testing has been run against the verification endpoint.
- No shared circuit-breaker state machine — each external integration has
  its own per-call timeout and degrades independently.
- Evidence upload (screenshots/email headers on reports) is not wired to
  object storage.
