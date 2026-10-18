import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity.deps import require_student_with_consent
from app.modules.identity.models import User
from app.modules.interview import service
from app.modules.interview.questions import QUESTIONS
from app.modules.interview.schemas import (
    AnswerRequest,
    AnswerResult,
    QuestionOut,
    SessionOut,
    StartRequest,
)

router = APIRouter(prefix="/interview", tags=["interview"])


@router.get("/questions", response_model=list[QuestionOut])
def list_questions(
    language: Literal["ta", "en"] | None = None,
    user: User = Depends(require_student_with_consent),
):
    """The whole question bank, localised. Lets the profile screen edit any field."""
    lang = language or user.preferred_language
    return [service.question_out(q, lang) for q in QUESTIONS]


@router.post("/sessions", response_model=SessionOut)
def start_or_resume(
    data: StartRequest | None = None,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    session = service.start_session(db, user, data.language if data else None)
    return service.session_out(db, session)


@router.get("/sessions/current", response_model=SessionOut)
def get_current(user: User = Depends(require_student_with_consent), db: Session = Depends(get_db)):
    try:
        session = service.current_session(db, user)
    except service.SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no_active_session") from None
    return service.session_out(db, session)


@router.post("/sessions/{session_id}/answers", response_model=AnswerResult)
def answer(
    session_id: uuid.UUID,
    data: AnswerRequest,
    request: Request,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    """Answer the current question, or any earlier one to correct it."""
    try:
        session, result = service.submit_answer(db, request.app.state.llm, user, session_id, data)
    except service.SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session_not_found") from None
    except service.SessionClosed:
        raise HTTPException(status.HTTP_409_CONFLICT, "session_completed") from None
    except service.UnknownQuestion:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_question") from None
    except service.InvalidAnswer:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_answer") from None
    except service.TooManyAnswers:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_answers") from None
    return AnswerResult(**result, session=service.session_out(db, session))
