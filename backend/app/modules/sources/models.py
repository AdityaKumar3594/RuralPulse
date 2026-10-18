from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, Computed, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, str_enum


class Verification(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"


class Publication(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


def _now() -> datetime:
    return datetime.now(UTC)


class Source(Base):
    """A trusted publisher of opportunities. Registry only: we link to it, we do not scrape it."""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[dict[str, str]] = mapped_column(JSONB)
    publisher: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(30))
    allowed_domains: Mapped[list[str]] = mapped_column(JSONB)
    api_access: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        Index("ix_opportunities_search_vector", "search_vector", postgresql_using="gin"),
    )

    slug: Mapped[str] = mapped_column(String(60), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[dict[str, str]] = mapped_column(JSONB)
    summary: Mapped[dict[str, str]] = mapped_column(JSONB)
    provider: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(300))
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    scope: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Structured claims; null/empty unless the record's verified_fields say they were checked.
    eligibility: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    required_documents: Mapped[list[str]] = mapped_column(JSONB, default=list)
    application_deadline: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    benefits: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    verification_status: Mapped[Verification] = mapped_column(
        str_enum(Verification, "opportunity_verification"), default=Verification.UNVERIFIED
    )
    verified_fields: Mapped[list[str]] = mapped_column(JSONB, default=list)
    verified_at: Mapped[date | None] = mapped_column(Date)
    verified_by: Mapped[str | None] = mapped_column(String(100))
    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence: Mapped[list[dict[str, str]]] = mapped_column(JSONB, default=list)
    publication_status: Mapped[Publication] = mapped_column(
        str_enum(Publication, "publication"), default=Publication.PUBLISHED
    )
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    search_text: Mapped[str] = mapped_column(Text)
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', search_text)", persisted=True)
    )
