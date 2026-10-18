#!/usr/bin/env bash
# Starts everything needed to try the prototype locally. Logs go to /tmp/Ruralpulse-*.log.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${BACKEND_PORT:-8100}"

command -v docker >/dev/null || { echo "Docker is required (for PostgreSQL)."; exit 1; }
docker info >/dev/null 2>&1 || { echo "Start Docker Desktop first, then run again."; exit 1; }

[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -d frontend/node_modules ] || (cd frontend && npm ci)
(cd backend && uv sync -q)

docker compose up -d --wait postgres
(cd backend && uv run alembic upgrade head)
(cd backend && uv run python -m app.ingestion.cli load)
(cd backend && uv run python -m app.admin.demo)

pkill -f "uvicorn app.main:app --port $PORT" 2>/dev/null || true
pkill -f "vite --port 5173" 2>/dev/null || true
(cd backend && nohup uv run uvicorn app.main:app --port "$PORT" >/tmp/Ruralpulse-backend.log 2>&1 &)
(cd frontend && API_PROXY_TARGET="http://localhost:$PORT" nohup npx vite --port 5173 --strictPort >/tmp/Ruralpulse-frontend.log 2>&1 &)

for _ in $(seq 1 60); do
  curl -sf "http://localhost:5173/api/health" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf "http://localhost:5173/api/health" || { echo "Backend did not start; see /tmp/Ruralpulse-backend.log"; exit 1; }
echo
echo "Ruralpulse is running:  http://localhost:5173"
echo "API docs:          http://localhost:$PORT/api/docs"
echo "Stop with:         make stop"
