from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity.deps import require_student_with_consent
from app.modules.identity.models import User
from app.modules.recommend import service
from app.modules.recommend.schemas import RecommendRequest, RunOut

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
def create_run(
    data: RecommendRequest,
    request: Request,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    """Rank careers for the signed-in student. Deterministic and explainable; no AI involved."""
    run = service.run_for_student(db, user, request.app.state.ranking_config, data.limit)
    return service.run_out(db, run, data.language, request.app.state.settings.source_fresh_days)


@router.get("/latest", response_model=RunOut)
def latest(
    request: Request,
    language: Literal["ta", "en"] = Query(default="en"),
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    run = service.latest_run(db, user)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no_recommendations_yet")
    return service.run_out(db, run, language, request.app.state.settings.source_fresh_days)
