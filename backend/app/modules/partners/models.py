import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, str_enum


def _now() -> datetime:
    return datetime.now(UTC)


class ProviderKind(StrEnum):
    EMPLOYER = "employer"
    NGO = "ngo"
    TRAINING_PROVIDER = "training_provider"
    MENTOR = "mentor"
    GOVERNMENT = "government"


class ProviderStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    SUSPENDED = "suspended"


class SubmissionStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150))
    kind: Mapped[ProviderKind] = mapped_column(str_enum(ProviderKind, "provider_kind"))
    website: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProviderStatus] = mapped_column(
        str_enum(ProviderStatus, "provider_status"), default=ProviderStatus.PENDING
    )
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"))  # set on approval
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ProviderMember(Base):
    __tablename__ = "provider_members"

    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("providers.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)


class OpportunitySubmission(Base):
    """A partner's proposal. Nothing here is published, and nothing becomes 'verified', until an
    administrator reviews it and explicitly verifies the claims they have evidence for."""

    __tablename__ = "opportunity_submissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("providers.id"), index=True)
    submitted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[SubmissionStatus] = mapped_column(
        str_enum(SubmissionStatus, "submission_status", 30), default=SubmissionStatus.DRAFT
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Set when this revises an already published opportunity (same slug is updated on approval).
    replaces_slug: Mapped[str | None] = mapped_column(ForeignKey("opportunities.slug"))
    review_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_slug: Mapped[str | None] = mapped_column(ForeignKey("opportunities.slug"))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
