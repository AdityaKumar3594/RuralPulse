from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core.db import check_database

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    db: Literal["ok", "error"]
    version: str


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    # Always 200 so clients can show a precise "degraded" state instead of a generic error.
    db_ok = await run_in_threadpool(check_database, request.app.state.engine)
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db="ok" if db_ok else "error",
        version=request.app.state.settings.app_version,
    )
