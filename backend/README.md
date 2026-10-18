# Ruralpulse backend

FastAPI modular monolith. See `../docs/ARCHITECTURE.md`.

```sh
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8100
```
