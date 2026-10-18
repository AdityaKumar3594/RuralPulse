import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, str_enum


class Provenance(StrEnum):
    REPORTED = "reported"  # stated by the student
    OBSERVED = "observed"  # evidence from an assessment, project or authorised observation
    HYPOTHESIS = "hypothesis"  # unconfirmed possibility
    UNKNOWN = "unknown"  # explicitly established as not known


class Verification(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"


class Slot(StrEnum):
    """Entries in the same slot supersede each other; different slots coexist."""

    SELF = "self"  # reported + unknown: the student's own statement
    OBSERVED = "observed"
    HYPOTHESIS = "hypothesis"


def _now() -> datetime:
    return datetime.now(UTC)


class ProfileEntry(Base):
    """Append-only history. The current value of a slot is the row with superseded_at IS NULL."""

    __tablename__ = "profile_entries"
    __table_args__ = (
        Index(
            "uq_profile_entries_current_slot",
            "user_id",
            "key",
            "slot",
            unique=True,
            postgresql_where=text("superseded_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    key: Mapped[str] = mapped_column(String(50))
    slot: Mapped[Slot] = mapped_column(str_enum(Slot, "slot"))
    provenance: Mapped[Provenance] = mapped_column(str_enum(Provenance, "provenance"))
    value: Mapped[Any | None] = mapped_column(JSONB)
    verification: Mapped[Verification] = mapped_column(
        str_enum(Verification, "verification"), default=Verification.UNVERIFIED
    )
    # Where it came from, e.g. "student_form", "interview:<question_id>", "facilitator".
    source: Mapped[str] = mapped_column(String(80))
    # Required for observed/hypothesis: the evidence or reasoning behind the entry.
    basis: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
