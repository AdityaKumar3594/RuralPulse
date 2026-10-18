import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class PathwayPlan(Base):
    __tablename__ = "pathway_plans"
    __table_args__ = (Index("ix_pathway_plans_user_career", "user_id", "career_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    career_slug: Mapped[str] = mapped_column(ForeignKey("careers.slug"))
    version: Mapped[str] = mapped_column(String(20))
    student_stage: Mapped[str | None] = mapped_column(String(30))  # stage the plan was built for
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    alternatives: Mapped[list[str]] = mapped_column(JSONB)
    unknowns: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PathwayStepProgress(Base):
    __tablename__ = "pathway_step_progress"

    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pathway_plans.id"), primary_key=True)
    step_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
