from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, Computed, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Career(Base):
    __tablename__ = "careers"
    __table_args__ = (Index("ix_careers_search_vector", "search_vector", postgresql_using="gin"),)

    slug: Mapped[str] = mapped_column(String(60), primary_key=True)
    family: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[dict[str, str]] = mapped_column(JSONB)
    description: Mapped[dict[str, str]] = mapped_column(JSONB)
    activities: Mapped[dict[str, list[str]]] = mapped_column(JSONB)
    skills: Mapped[dict[str, list[str]]] = mapped_column(JSONB)
    entry: Mapped[dict[str, Any]] = mapped_column(JSONB)
    routes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    related: Mapped[list[str]] = mapped_column(JSONB, default=list)
    learning_resources: Mapped[list[str]] = mapped_column(JSONB, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    source_refs: Mapped[list[dict[str, str]]] = mapped_column(JSONB, default=list)
    # Catalog entries are curated drafts until a person checks them against official sources.
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    localization_status: Mapped[str] = mapped_column(String(30), default="unreviewed")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    search_text: Mapped[str] = mapped_column(Text)
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', search_text)", persisted=True)
    )
