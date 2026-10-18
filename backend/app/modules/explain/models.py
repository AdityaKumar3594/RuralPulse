import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Explanation(Base):
    """Every explanation shown: AI or template, with why a template was used if so."""

    __tablename__ = "explanations"
    __table_args__ = (Index("ix_explanations_user_hash", "user_id", "evidence_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(8))
    source: Mapped[str] = mapped_column(String(10))  # "ai" | "template"
    fallback_reason: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(60))
    evidence_hash: Mapped[str] = mapped_column(String(64))
    output: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
