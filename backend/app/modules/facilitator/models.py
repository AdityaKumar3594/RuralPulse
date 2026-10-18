import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, str_enum


def _now() -> datetime:
    return datetime.now(UTC)


class EndorsementStatus(StrEnum):
    SUGGESTED = "suggested"
    SEEN = "seen"
    DISMISSED = "dismissed"


class ReviewDecision(StrEnum):
    AGREE = "agree"
    DISAGREE = "disagree"
    NEEDS_DISCUSSION = "needs_discussion"


class HelpTopic(StrEnum):
    GENERAL = "general"
    INTERVIEW = "interview"
    PATHWAY = "pathway"
    APPLICATION = "application"


class HelpStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class FacilitatorAssignment(Base):
    """Which facilitator may work with which student. Created by an administrator only."""

    __tablename__ = "facilitator_assignments"
    __table_args__ = (
        Index(
            "uq_facilitator_assignments_active",
            "facilitator_id",
            "student_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    facilitator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Endorsement(Base):
    """A facilitator suggests an opportunity to a student they have spotted talent in."""

    __tablename__ = "endorsements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    facilitator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    opportunity_slug: Mapped[str] = mapped_column(ForeignKey("opportunities.slug"))
    note: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[EndorsementStatus] = mapped_column(
        str_enum(EndorsementStatus, "endorsement_status"), default=EndorsementStatus.SUGGESTED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RecommendationReview(Base):
    __tablename__ = "recommendation_reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    facilitator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recommendation_runs.id"))
    career_slug: Mapped[str] = mapped_column(ForeignKey("careers.slug"))
    decision: Mapped[ReviewDecision] = mapped_column(
        str_enum(ReviewDecision, "review_decision", 30)
    )
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HelpRequest(Base):
    __tablename__ = "help_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    topic: Mapped[HelpTopic] = mapped_column(str_enum(HelpTopic, "help_topic"))
    message: Mapped[str | None] = mapped_column(Text)
    opportunity_slug: Mapped[str | None] = mapped_column(ForeignKey("opportunities.slug"))
    status: Mapped[HelpStatus] = mapped_column(
        str_enum(HelpStatus, "help_status"), default=HelpStatus.OPEN
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
