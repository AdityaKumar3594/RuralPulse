import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class EligibilityEvaluation(Base):
    """Immutable record of one evaluation: what was decided, by which rules, from which facts."""

    __tablename__ = "eligibility_evaluations"
    __table_args__ = (Index("ix_eligibility_user_opportunity", "user_id", "opportunity_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    opportunity_slug: Mapped[str] = mapped_column(ForeignKey("opportunities.slug"))
    outcome: Mapped[str] = mapped_column(String(20))
    reasons: Mapped[list[str]] = mapped_column(JSONB)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    missing: Mapped[list[str]] = mapped_column(JSONB)
    flags: Mapped[list[str]] = mapped_column(JSONB)
    facts_used: Mapped[dict[str, Any]] = mapped_column(JSONB)
    rules_version: Mapped[str] = mapped_column(String(20))
    # Hash of the opportunity rules at evaluation time: shows if the record changed since.
    opportunity_fingerprint: Mapped[str] = mapped_column(String(64))
    # Verification state of the record that the rules came from.
    record_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    evaluated_on: Mapped[date] = mapped_column(Date)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
