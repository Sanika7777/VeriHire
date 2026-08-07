.PHONY: dev api web worker migrate upgrade seed test e2e lint ml.data ml.train ml.eval

dev:
	docker compose up --build

api:
	cd apps/api && uv run uvicorn app.main:app --reload

web:
	pnpm --filter @verihire/web dev

worker:
	cd apps/api && uv run arq app.workers.worker.WorkerSettings

migrate:
	cd apps/api && uv run alembic revision --autogenerate -m "$(m)"

upgrade:
	cd apps/api && uv run alembic upgrade head

seed:
	cd apps/api && uv run python -m app.db.seed

test:
	cd apps/api && uv run pytest
	pnpm --filter @verihire/web test

e2e:
	pnpm --filter @verihire/web exec playwright test

lint:
	cd apps/api && uv run ruff check . && uv run mypy app
	pnpm --filter @verihire/web lint
	pnpm --filter @verihire/web typecheck

ml.data:
	cd services/ml && uv run python -m src.ingest

ml.train:
	cd services/ml && uv run python -m src.train

ml.eval:
	cd services/ml && uv run python -m src.evaluate
