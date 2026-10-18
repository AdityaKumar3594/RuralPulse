import uuid
from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, str_enum


class Role(StrEnum):
    STUDENT = "student"
    FACILITATOR = "facilitator"
    PARTNER = "partner"
    ADMIN = "admin"


class ConsentGivenBy(StrEnum):
    SELF = "self"
    GUARDIAN = "guardian"


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    role: Mapped[Role] = mapped_column(str_enum(Role, "role"))
    phone: Mapped[str] = mapped_column(String(10), unique=True)
    pin_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100))
    # Needed to decide whether guardian consent is required and for age-based eligibility.
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    preferred_language: Mapped[str] = mapped_column(String(8), default="ta")
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (
        # At most one active (not withdrawn) consent per user and purpose.
        Index(
            "uq_consents_active_user_purpose",
            "user_id",
            "purpose",
            unique=True,
            postgresql_where=text("withdrawn_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(40))
    policy_version: Mapped[str] = mapped_column(String(30))
    given_by: Mapped[ConsentGivenBy] = mapped_column(str_enum(ConsentGivenBy, "given_by"))
    guardian_name: Mapped[str | None] = mapped_column(String(100))
    guardian_phone: Mapped[str | None] = mapped_column(String(10))
    # Guardian identity is NOT verified by this system yet; the value says so explicitly.
    verification: Mapped[str] = mapped_column(String(20), default="self_declared")
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
