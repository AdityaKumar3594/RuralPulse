import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.base import LLMProvider
from app.core.audit import audit
from app.modules.identity.models import User
from app.modules.interview import selector
from app.modules.interview.interpreter import interpret_text
from app.modules.interview.models import InterviewAnswer, InterviewSession, Outcome, SessionStatus
from app.modules.interview.questions import (
    BY_ID,
    MESSAGES,
    QUESTION_BANK_VERSION,
    QUESTIONS,
    Question,
    localize,
)
from app.modules.interview.schemas import AnswerRequest
from app.modules.profile import service as profile_service
from app.modules.profile.models import Provenance

MAX_CLARIFICATIONS = 2  # after this many failed attempts we move on rather than trap the student
MAX_ANSWERS_PER_SESSION = 100  # bounds LLM spend per session


class InterviewError(Exception):
    pass


class SessionNotFound(InterviewError):
    pass


class SessionClosed(InterviewError):
    pass


class UnknownQuestion(InterviewError):
    pass


class InvalidAnswer(InterviewError):
    pass


class TooManyAnswers(InterviewError):
    pass


def snapshot(db: Session, user_id: uuid.UUID) -> selector.ProfileSnapshot:
    entries = profile_service.current_entries(db, user_id)
    answered = {
        e.key
        for e in entries
        if e.provenance in (Provenance.REPORTED, Provenance.UNKNOWN, Provenance.OBSERVED)
    }
    values: dict[str, Any] = {}
    # Observed first, then reported: what the student says decides routing when they differ.
    for provenance in (Provenance.OBSERVED, Provenance.REPORTED):
        values.update({e.key: e.value for e in entries if e.provenance is provenance and e.value})
    return selector.ProfileSnapshot(frozenset(answered), values)


def question_out(question: Question, lang: str) -> dict[str, Any]:
    return {
        "id": question.id,
        "field_key": question.field_key,
        "kind": question.kind,
        "prompt": localize(question.prompt, lang),
        "why": localize(question.why, lang),
        "options": [{"value": o.value, "label": localize(o.label, lang)} for o in question.options],
        "min_value": question.min_value,
        "max_value": question.max_value,
    }


def session_out(db: Session, session: InterviewSession) -> dict[str, Any]:
    snap = snapshot(db, session.user_id)
    question = None
    if session.status is SessionStatus.ACTIVE:
        nxt = selector.next_question(QUESTIONS, snap, session.skipped_question_ids)
        question = question_out(nxt, session.language) if nxt else None
    answered, total = selector.progress(QUESTIONS, snap)
    return {
        "id": session.id,
        "status": session.status.value,
        "language": session.language,
        "question": question,
        "progress": {"answered": answered, "total": total},
    }


def _active_session(db: Session, user_id: uuid.UUID) -> InterviewSession | None:
    return db.scalar(
        select(InterviewSession).where(
            InterviewSession.user_id == user_id, InterviewSession.status == SessionStatus.ACTIVE
        )
    )


def _complete_if_done(db: Session, session: InterviewSession) -> None:
    snap = snapshot(db, session.user_id)
    if selector.next_question(QUESTIONS, snap, session.skipped_question_ids) is None:
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(UTC)
        audit(db, "interview.completed", actor_id=session.user_id, subject_user_id=session.user_id)


def start_session(db: Session, user: User, language: str | None) -> InterviewSession:
    """Resume the active session if there is one; otherwise start a fresh one."""
    existing = _active_session(db, user.id)
    if existing is not None:
        return existing
    session = InterviewSession(
        user_id=user.id,
        language=language or user.preferred_language,
        question_bank_version=QUESTION_BANK_VERSION,
        skipped_question_ids=[],
        clarification_counts={},
    )
    db.add(session)
    db.flush()
    audit(db, "interview.started", actor_id=user.id, subject_user_id=user.id)
    _complete_if_done(db, session)  # nothing left to ask: complete straight away
    db.commit()
    return session


def current_session(db: Session, user: User) -> InterviewSession:
    session = _active_session(db, user.id)
    if session is None:
        raise SessionNotFound
    return session


def submit_answer(
    db: Session, llm: LLMProvider | None, user: User, session_id: uuid.UUID, req: AnswerRequest
) -> tuple[InterviewSession, dict[str, Any]]:
    session = db.get(InterviewSession, session_id)
    if session is None or session.user_id != user.id:
        raise SessionNotFound
    if session.status is not SessionStatus.ACTIVE:
        raise SessionClosed
    question = BY_ID.get(req.question_id)
    if question is None:
        raise UnknownQuestion
    answer_count = db.scalar(
        select(func.count())
        .select_from(InterviewAnswer)
        .where(InterviewAnswer.session_id == session.id)
    )
    if answer_count >= MAX_ANSWERS_PER_SESSION:
        raise TooManyAnswers

    lang = session.language
    was_answered = question.field_key in snapshot(db, user.id).answered
    outcome: Outcome
    interpreted_by: str | None = None
    message: str | None = None
    extracted: dict[str, Any] | None = None
    source = f"interview:{question.id}"

    def record(provenance: Provenance, value: Any, source: str) -> None:
        try:
            profile_service.record_entry(
                db,
                user_id=user.id,
                key=question.field_key,
                value=value,
                provenance=provenance,
                source=source,
                recorded_by=user.id,
                commit=False,
            )
        except profile_service.InvalidValue:
            db.rollback()
            raise InvalidAnswer from None

    if req.kind == "skip":
        outcome = Outcome.SKIPPED
        if not was_answered and question.id not in session.skipped_question_ids:
            session.skipped_question_ids = [*session.skipped_question_ids, question.id]
    elif req.kind == "unknown":
        record(Provenance.UNKNOWN, None, source)
        outcome = Outcome.UNKNOWN
    elif req.kind == "value":
        record(Provenance.REPORTED, req.value, source)
        outcome, interpreted_by = Outcome.RECORDED, "student"
    else:
        result = interpret_text(question, req.text or "", llm)
        extracted = result.detail
        if result.status == "ok":
            ai = result.by == "ai"
            record(Provenance.REPORTED, result.value, source + (":ai" if ai else ""))
            outcome, interpreted_by = Outcome.RECORDED, result.by
        else:
            counts = dict(session.clarification_counts)
            counts[question.id] = counts.get(question.id, 0) + 1
            session.clarification_counts = counts
            if counts[question.id] >= MAX_CLARIFICATIONS:
                outcome = Outcome.SKIPPED
                message = localize(MESSAGES["moving_on"], lang)
                session.skipped_question_ids = [*session.skipped_question_ids, question.id]
            else:
                outcome = Outcome.NEEDS_CLARIFICATION
                key = "clarify_choice" if question.options else "clarify_text"
                message = localize(MESSAGES[key], lang)

    db.add(
        InterviewAnswer(
            session_id=session.id,
            question_id=question.id,
            input_kind=req.kind,
            outcome=outcome,
            raw_text=req.text if req.kind == "text" else None,
            interpreted_by=interpreted_by,
            extracted=extracted,
        )
    )
    db.flush()
    _complete_if_done(db, session)
    db.commit()
    corrected = was_answered and outcome in (Outcome.RECORDED, Outcome.UNKNOWN)
    return session, {
        "outcome": outcome.value,
        "corrected": corrected,
        "interpreted_by": interpreted_by,
        "message": message,
    }
