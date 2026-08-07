# VeriHire

VeriHire lets job seekers verify recruiters, companies and job postings before
they apply, and lets the community report recruitment fraud. Every result is
a **Trust Score (0–100)** with a full, explainable breakdown across identity,
company legitimacy, ML-derived content risk, link safety and community
signal — never a black box.

## Architecture

| Surface | Path | Stack |
|---|---|---|
| Job seeker app, marketing, admin console, company portal | `apps/web` | Next.js 15 (App Router, RSC, TypeScript strict), Tailwind v4, shadcn/ui |
| API | `apps/api` | FastAPI (async), SQLAlchemy 2.0 + Alembic, PostgreSQL 16 (`pg_trgm`, `pgvector`), Redis 7, ARQ workers |
| ML | `services/ml` | TF-IDF/LightGBM fraud model with SHAP explanations, phishing-URL model |

See [`CLAUDE.md`](./CLAUDE.md) for the full technical and product spec,
[`PHASES.md`](./PHASES.md) for the build plan, and [`DATA.md`](./DATA.md) for
dataset provenance.

## Prerequisites

- Node.js ≥ 20 with [pnpm](https://pnpm.io) (`corepack enable` will provide it)
- Python 3.12 with [uv](https://docs.astral.sh/uv/)
- Docker + Docker Compose (for Postgres, Redis, MinIO, MailHog)

## Local setup

```bash
git clone <repo-url> verihire
cd verihire
cp .env.example .env        # fill in secrets for anything beyond local dev

# install dependencies
pnpm install
cd apps/api && uv sync && cd ../..

# bring up the full stack (postgres, redis, minio, mailhog, api, web, worker)
make dev
```

Once the stack is healthy:

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs
- API readiness: http://localhost:8000/ready
- MailHog UI: http://localhost:8025
- MinIO console: http://localhost:9001

### Running pieces individually (without Docker)

```bash
make api      # uvicorn --reload on :8000
make web      # next dev --turbopack on :3000
make worker   # ARQ worker process
```

You'll need Postgres and Redis reachable at the URLs in `.env` for these to
pass their readiness checks.

### Database

```bash
make upgrade          # apply migrations
make migrate m="add reports table"   # generate a new migration
make seed             # load realistic seed data
```

### Tests & linting

```bash
make lint   # ruff + mypy --strict (api), eslint + tsc --noEmit (web)
make test   # pytest (api), vitest (web)
make e2e    # playwright
```

### ML pipeline

```bash
make ml.data    # verify/prepare the raw datasets in services/ml/data/raw
make ml.train   # train + evaluate, write services/ml/artifacts/v{n}/
make ml.eval    # evaluate the current artifact against the held-out split
```

## Repository layout

See `CLAUDE.md` §4 for the full annotated layout.

## Decisions worth knowing

- **Scores are advisory, never a determination of guilt.** See
  `docs/limitations.md` (Phase 11) for the full honesty statement surfaced in
  the product footer.
- **Weights for the Trust Score are versioned data, not code** — see the
  `scoring_configs` table and the admin scoring editor (Phase 9).
- **A confirmed fraud report hard-caps a score at 25** regardless of other
  sub-scores.

## Status

This repository is under active, phased construction per `PHASES.md`. See
that file's progress table for what's currently shipped.
