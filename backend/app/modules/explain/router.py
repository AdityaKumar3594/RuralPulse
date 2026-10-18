from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.explain import service
from app.modules.explain.schemas import ExplainRequest, ExplanationOut
from app.modules.identity.deps import require_student_with_consent
from app.modules.identity.models import User

router = APIRouter(prefix="/explanations", tags=["explanations"])


@router.post("", response_model=ExplanationOut, status_code=status.HTTP_201_CREATED)
def create(
    data: ExplainRequest,
    request: Request,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    """Explain a computed result in simple language.

    The AI (when configured) only rewrites facts that already exist; its text is checked against
    the evidence and replaced by a fixed template if anything is not backed. The eligibility
    verdict always comes from the rules engine.
    """
    try:
        return service.explain(
            db,
            request.app.state.llm,
            request.app.state.settings,
            user,
            data.kind,
            data.ref(),
            data.language,
        )
    except service.RefNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found") from None
    except service.BadRef:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "bad_reference") from None
