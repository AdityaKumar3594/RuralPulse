BACKEND_PORT ?= 8100
TEST_DATABASE_URL ?= postgresql+psycopg://Ruralpulse:Ruralpulse@localhost:5432/Ruralpulse_test

DEMO_NOTE = 'Demo accounts have public PINs: never use on a real deployment'

.PHONY: demo-data run stop install db-up db-down migrate seed validate-seed check-links dev-backend dev-frontend test test-backend test-frontend lint build

install:
	cd backend && uv sync
	cd frontend && npm ci

db-up:
	docker compose up -d --wait postgres

db-down:
	docker compose down

migrate:
	cd backend && uv run alembic upgrade head

# Validate (no database) and load the curated careers, sources and opportunities.
validate-seed:
	cd backend && uv run python -m app.ingestion.cli validate

seed: validate-seed
	cd backend && uv run python -m app.ingestion.cli load

# Network check that seed URLs still respond (run by hand; some sites block scripts).
check-links:
	cd backend && uv run --with certifi python ../scripts/check_seed_links.py

# Throw-away demo accounts (see backend/app/admin/demo.py for the logins).
demo-data:
	@echo $(DEMO_NOTE)
	cd backend && uv run python -m app.admin.demo

# One command: database, migrations, seed data, demo accounts, then backend + frontend.
run:
	./scripts/run_demo.sh

stop:
	-pkill -f "uvicorn app.main:app --port $(BACKEND_PORT)"
	-pkill -f "vite --port 5173"

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --port $(BACKEND_PORT)

dev-frontend:
	cd frontend && API_PROXY_TARGET=http://localhost:$(BACKEND_PORT) npm run dev

test: test-backend test-frontend

# Database tests run when TEST_DATABASE_URL is reachable (start it with `make db-up`).
test-backend:
	cd backend && TEST_DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest

test-frontend:
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint && npm run typecheck

build:
	cd frontend && npm run build
