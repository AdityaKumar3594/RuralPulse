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


class PriceType(StrEnum):
    FREE = "free"
    PER_MODULE = "per_module"
    SUBSCRIPTION = "subscription"


class ModuleStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class PaymentStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    # There is no payment gateway in this prototype, so a paid module can be reserved but never
    # paid for, and its lessons stay locked.
    UNPAID_NO_GATEWAY = "unpaid_no_gateway"


class TrainingModule(Base):
    __tablename__ = "training_modules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    facilitator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(8))
    lessons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    price_type: Mapped[PriceType] = mapped_column(
        str_enum(PriceType, "price_type"), default=PriceType.FREE
    )
    price_inr: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[ModuleStatus] = mapped_column(
        str_enum(ModuleStatus, "module_status"), default=ModuleStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class ModuleEnrollment(Base):
    __tablename__ = "module_enrollments"

    module_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("training_modules.id"), primary_key=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        str_enum(PaymentStatus, "payment_status", 30), default=PaymentStatus.NOT_REQUIRED
    )
    completed_lessons: Mapped[list[int]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
