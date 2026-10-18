import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.modules.identity.models import User
from app.modules.training.models import (
    ModuleEnrollment,
    ModuleStatus,
    PaymentStatus,
    PriceType,
    TrainingModule,
)


class TrainingError(Exception):
    pass


class NotFound(TrainingError):
    pass


class Conflict(TrainingError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def own_module(db: Session, facilitator: User, module_id: uuid.UUID) -> TrainingModule:
    module = db.get(TrainingModule, module_id)
    if module is None or module.facilitator_id != facilitator.id:
        raise NotFound
    return module


def check_pricing(price_type: PriceType, price_inr: int | None) -> None:
    if price_type is PriceType.FREE and price_inr is not None:
        raise Conflict("free_module_has_no_price")
    if price_type is not PriceType.FREE and not price_inr:
        raise Conflict("price_required")


def create_module(db: Session, facilitator: User, data: dict[str, Any]) -> TrainingModule:
    check_pricing(data["price_type"], data.get("price_inr"))
    module = TrainingModule(facilitator_id=facilitator.id, **data)
    db.add(module)
    audit(db, "module.created", actor_id=facilitator.id)
    db.commit()
    return module


def update_module(db: Session, facilitator: User, module_id: uuid.UUID, data: dict[str, Any]):
    module = own_module(db, facilitator, module_id)
    merged_type = data.get("price_type", module.price_type)
    merged_price = data.get("price_inr", module.price_inr)
    if merged_type is PriceType.FREE and "price_type" in data:
        merged_price = None
        data["price_inr"] = None
    check_pricing(merged_type, merged_price)
    for key, value in data.items():
        setattr(module, key, value)
    db.commit()
    return module


def publish(db: Session, facilitator: User, module_id: uuid.UUID) -> TrainingModule:
    module = own_module(db, facilitator, module_id)
    if not module.lessons:
        raise Conflict("needs_at_least_one_lesson")
    module.status = ModuleStatus.PUBLISHED
    audit(db, "module.published", actor_id=facilitator.id, module=str(module.id))
    db.commit()
    return module


def withdraw(db: Session, facilitator: User, module_id: uuid.UUID) -> TrainingModule:
    module = own_module(db, facilitator, module_id)
    module.status = ModuleStatus.WITHDRAWN
    audit(db, "module.withdrawn", actor_id=facilitator.id, module=str(module.id))
    db.commit()
    return module


def facilitator_modules(db: Session, facilitator: User) -> list[dict[str, Any]]:
    out = []
    for m in db.scalars(
        select(TrainingModule)
        .where(TrainingModule.facilitator_id == facilitator.id)
        .order_by(TrainingModule.created_at.desc())
    ):
        count = db.scalar(
            select(func.count())
            .select_from(ModuleEnrollment)
            .where(ModuleEnrollment.module_id == m.id)
        )
        out.append({"module": m, "enrollments": count})
    return out


def published_modules(db: Session) -> list[TrainingModule]:
    return list(
        db.scalars(
            select(TrainingModule)
            .where(TrainingModule.status == ModuleStatus.PUBLISHED)
            .order_by(TrainingModule.created_at.desc())
        )
    )


def get_published(db: Session, module_id: uuid.UUID) -> TrainingModule:
    module = db.get(TrainingModule, module_id)
    if module is None or module.status is not ModuleStatus.PUBLISHED:
        raise NotFound
    return module


def enrollment_for(db: Session, student: User, module_id: uuid.UUID) -> ModuleEnrollment | None:
    return db.get(ModuleEnrollment, (module_id, student.id))


def enroll(db: Session, student: User, module_id: uuid.UUID) -> tuple[ModuleEnrollment, bool]:
    module = get_published(db, module_id)
    existing = enrollment_for(db, student, module.id)
    if existing is not None:
        return existing, False
    paid = module.price_type is not PriceType.FREE
    enrollment = ModuleEnrollment(
        module_id=module.id,
        student_id=student.id,
        # No payment gateway exists, so a paid module can only be reserved, never paid for.
        payment_status=PaymentStatus.UNPAID_NO_GATEWAY if paid else PaymentStatus.NOT_REQUIRED,
        completed_lessons=[],
    )
    db.add(enrollment)
    audit(
        db,
        "module.enrolled",
        actor_id=student.id,
        subject_user_id=student.id,
        module=str(module.id),
    )
    db.commit()
    return enrollment, True


def has_access(module: TrainingModule, enrollment: ModuleEnrollment | None) -> bool:
    return enrollment is not None and enrollment.payment_status is PaymentStatus.NOT_REQUIRED


def complete_lesson(
    db: Session, student: User, module_id: uuid.UUID, index: int, done: bool
) -> ModuleEnrollment:
    module = get_published(db, module_id)
    enrollment = enrollment_for(db, student, module.id)
    if enrollment is None:
        raise NotFound
    if not has_access(module, enrollment):
        raise Conflict("payment_not_available")
    if not 0 <= index < len(module.lessons):
        raise NotFound
    lessons = set(enrollment.completed_lessons)
    lessons.add(index) if done else lessons.discard(index)
    enrollment.completed_lessons = sorted(lessons)
    db.commit()
    return enrollment


def module_out(
    module: TrainingModule, enrollment: ModuleEnrollment | None, *, facilitator_view: bool = False
) -> dict[str, Any]:
    access = facilitator_view or has_access(module, enrollment)
    return {
        "id": module.id,
        "title": module.title,
        "description": module.description,
        "language": module.language,
        "status": module.status.value,
        "price_type": module.price_type.value,
        "price_inr": module.price_inr,
        "lesson_titles": [lesson["title"] for lesson in module.lessons],
        # Lessons stay locked until the student has access. Paid modules cannot be unlocked
        # here, because there is no payment gateway.
        "lessons": module.lessons if access else None,
        "enrolled": enrollment is not None,
        "payment_status": enrollment.payment_status.value if enrollment else None,
        "access": access,
        "completed_lessons": enrollment.completed_lessons if enrollment else [],
        "payments_available": False,
        "created_at": module.created_at,
    }
