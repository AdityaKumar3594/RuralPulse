import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, str_enum


class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"


class Outcome(StrEnum):
    RECORDED = "recorded"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"
    NEEDS_CLARIFICATION = "needs_clarification"


def _now() -> datetime:
    return datetime.now(UTC)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    __table_args__ = (
        # One active (resumable) session per student.
        Index(
            "uq_interview_sessions_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    language: Mapped[str] = mapped_column(String(8))
    question_bank_version: Mapped[str] = mapped_column(String(20))
    status: Mapped[SessionStatus] = mapped_column(
        str_enum(SessionStatus, "session_status"), default=SessionStatus.ACTIVE
    )
    # Questions the student chose to skip (or we gave up clarifying) in this session.
    skipped_question_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    clarification_counts: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InterviewAnswer(Base):
    """What the student submitted and how it was handled. The profile holds the resulting value."""

    __tablename__ = "interview_answers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_sessions.id"), index=True)
    question_id: Mapped[str] = mapped_column(String(50))
    input_kind: Mapped[str] = mapped_column(String(10))  # value | text | unknown | skip
    outcome: Mapped[Outcome] = mapped_column(str_enum(Outcome, "outcome", length=30))
    raw_text: Mapped[str | None] = mapped_column(Text)
    interpreted_by: Mapped[str | None] = mapped_column(String(20))
    extracted: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
