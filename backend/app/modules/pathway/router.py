import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity.deps import require_student_with_consent
from app.modules.identity.models import User
from app.modules.pathway import service
from app.modules.pathway.schemas import CreatePlanRequest, PlanOut, ProgressUpdate

router = APIRouter(prefix="/pathways", tags=["pathways"])

Lang = Query(default="en", pattern="^(ta|en)$")


def _days(request: Request) -> int:
    return request.app.state.settings.source_fresh_days


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(
    data: CreatePlanRequest,
    request: Request,
    response: Response,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    """Build (or return the existing) pathway for a career. Deterministic: no AI is used."""
    try:
        plan, created = service.create_plan(db, user, data.career, data.refresh)
    except service.CareerNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "career_not_found") from None
    if not created:
        response.status_code = status.HTTP_200_OK
    return service.plan_out(db, plan, data.language, _days(request))


@router.get("", response_model=list[PlanOut])
def list_plans(
    request: Request,
    language: Literal["ta", "en"] = Lang,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    return [service.plan_out(db, p, language, _days(request)) for p in service.list_plans(db, user)]


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(
    plan_id: uuid.UUID,
    request: Request,
    language: Literal["ta", "en"] = Lang,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    try:
        plan = service.get_plan(db, user, plan_id)
    except service.PlanNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "plan_not_found") from None
    return service.plan_out(db, plan, language, _days(request))


@router.put("/{plan_id}/steps/{step_id}", response_model=PlanOut)
def update_step(
    plan_id: uuid.UUID,
    step_id: str,
    data: ProgressUpdate,
    request: Request,
    language: Literal["ta", "en"] = Lang,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    try:
        plan = service.get_plan(db, user, plan_id)
        service.set_progress(db, plan, step_id, data.status, data.note, user.id)
    except service.PlanNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "plan_not_found") from None
    except service.UnknownStep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_step") from None
    except service.PrerequisitesNotDone:
        raise HTTPException(status.HTTP_409_CONFLICT, "prerequisites_not_done") from None
    except service.DependentStepsStarted:
        raise HTTPException(status.HTTP_409_CONFLICT, "dependent_steps_started") from None
    return service.plan_out(db, plan, language, _days(request))
