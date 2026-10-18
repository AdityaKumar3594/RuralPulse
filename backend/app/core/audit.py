import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


class AuditEvent(Base):
    """Append-only record of who did what. Never store secrets or profile values in `detail`."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(60))
    subject_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


def audit(
    db: Session,
    action: str,
    *,
    actor_id: uuid.UUID | None,
    subject_user_id: uuid.UUID | None = None,
    **detail: Any,
) -> None:
    """Stage an audit event in the caller's transaction (the caller commits)."""
    db.add(
        AuditEvent(
            action=action,
            actor_id=actor_id,
            subject_user_id=subject_user_id,
            detail=detail or None,
        )
    )
