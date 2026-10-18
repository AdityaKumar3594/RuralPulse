from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.eligibility import service
from app.modules.eligibility.schemas import EvaluateRequest, EvaluationOut
from app.modules.identity.deps import require_student_with_consent
from app.modules.identity.models import User
from app.modules.sources import service as sources

router = APIRouter(prefix="/eligibility", tags=["eligibility"])


@router.post("/evaluations", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
def evaluate(
    data: EvaluateRequest,
    request: Request,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    """Deterministic check of the signed-in student against one published opportunity.

    No AI is involved. The result is stored with the rule version and the facts used.
    """
    opp = sources.get_opportunity(db, data.opportunity)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "opportunity_not_found")
    row = service.evaluate_for_student(db, user, opp, request.app.state.settings.source_fresh_days)
    return service.evaluation_out(db, row, data.language)


@router.get("/evaluations", response_model=list[EvaluationOut])
def list_evaluations(
    opportunity: str | None = None,
    language: str = Query(default="en", pattern="^(ta|en)$"),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    return [
        service.evaluation_out(db, r, language)
        for r in service.history(db, user, opportunity, limit)
    ]
