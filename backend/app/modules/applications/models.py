import secrets
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, str_enum


def _now() -> datetime:
    return datetime.now(UTC)


def _reference_code() -> str:
    # Unambiguous characters only (no 0/O, 1/I), easy to read out over a phone call.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


class InternalStatus(StrEnum):
    """Our own tracking: what the student says they have done. Not proof of anything."""

    SAVED = "saved"
    PREPARING = "preparing"
    DOCUMENTS_READY = "documents_ready"
    APPLIED = "applied"  # the student says they applied on the official site
    WITHDRAWN = "withdrawn"


class ExternalStatus(StrEnum):
    """What the provider actually did with the application."""

    UNKNOWN = "unknown"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class StatusSource(StrEnum):
    STUDENT_REPORTED = "student_reported"  # unconfirmed
    FACILITATOR_CONFIRMED = "facilitator_confirmed"
    PROVIDER_CONFIRMED = "provider_confirmed"


CONFIRMED_SOURCES = {StatusSource.FACILITATOR_CONFIRMED, StatusSource.PROVIDER_CONFIRMED}


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        Index("uq_applications_user_opportunity", "user_id", "opportunity_slug", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    opportunity_slug: Mapped[str] = mapped_column(ForeignKey("opportunities.slug"))
    internal_status: Mapped[InternalStatus] = mapped_column(
        str_enum(InternalStatus, "internal_status", 30), default=InternalStatus.SAVED
    )
    note: Mapped[str | None] = mapped_column(Text)
    # Required documents copied when saved, with the student's own checklist ticks.
    documents: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    external_status: Mapped[ExternalStatus] = mapped_column(
        str_enum(ExternalStatus, "external_status", 30), default=ExternalStatus.UNKNOWN
    )
    external_status_source: Mapped[StatusSource | None] = mapped_column(
        str_enum(StatusSource, "external_status_source", 30)
    )
    external_status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_status_note: Mapped[str | None] = mapped_column(String(300))
    external_status_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    # Shared by the student with a provider so it can confirm status without seeing who they are.
    reference_code: Mapped[str] = mapped_column(String(8), unique=True, default=_reference_code)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
