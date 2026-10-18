import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity.deps import require_role, require_student_with_consent
from app.modules.identity.models import Role, User
from app.modules.training import service
from app.modules.training.schemas import (
    FacilitatorModuleOut,
    LessonProgressIn,
    ModuleIn,
    ModuleOut,
    ModuleUpdate,
)

router = APIRouter(tags=["training"])
require_facilitator = require_role(Role.FACILITATOR)


def _http(exc: service.TrainingError) -> HTTPException:
    if isinstance(exc, service.Conflict):
        return HTTPException(status.HTTP_409_CONFLICT, exc.code)
    return HTTPException(status.HTTP_404_NOT_FOUND, "not_found")


# --- facilitators author and run their own modules ---------------------------------------------


@router.post("/facilitator/modules", response_model=ModuleOut, status_code=status.HTTP_201_CREATED)
def create_module(
    data: ModuleIn, facilitator: User = Depends(require_facilitator), db: Session = Depends(get_db)
):
    try:
        module = service.create_module(db, facilitator, data.model_dump())
    except service.TrainingError as exc:
        raise _http(exc) from None
    return service.module_out(module, None, facilitator_view=True)


@router.get("/facilitator/modules", response_model=list[FacilitatorModuleOut])
def my_modules(facilitator: User = Depends(require_facilitator), db: Session = Depends(get_db)):
    return [
        {
            "module": service.module_out(r["module"], None, facilitator_view=True),
            "enrollments": r["enrollments"],
        }
        for r in service.facilitator_modules(db, facilitator)
    ]


@router.put("/facilitator/modules/{module_id}", response_model=ModuleOut)
def update_module(
    module_id: uuid.UUID,
    data: ModuleUpdate,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    try:
        module = service.update_module(
            db, facilitator, module_id, data.model_dump(exclude_unset=True)
        )
    except service.TrainingError as exc:
        raise _http(exc) from None
    return service.module_out(module, None, facilitator_view=True)


@router.post("/facilitator/modules/{module_id}/publish", response_model=ModuleOut)
def publish(
    module_id: uuid.UUID,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    try:
        return service.module_out(
            service.publish(db, facilitator, module_id), None, facilitator_view=True
        )
    except service.TrainingError as exc:
        raise _http(exc) from None


@router.post("/facilitator/modules/{module_id}/withdraw", response_model=ModuleOut)
def withdraw(
    module_id: uuid.UUID,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    try:
        return service.module_out(
            service.withdraw(db, facilitator, module_id), None, facilitator_view=True
        )
    except service.TrainingError as exc:
        raise _http(exc) from None


# --- students ----------------------------------------------------------------------------------


@router.get("/modules", response_model=list[ModuleOut])
def browse(user: User = Depends(require_student_with_consent), db: Session = Depends(get_db)):
    return [
        service.module_out(m, service.enrollment_for(db, user, m.id))
        for m in service.published_modules(db)
    ]


@router.get("/modules/{module_id}", response_model=ModuleOut)
def get_module(
    module_id: uuid.UUID,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    try:
        module = service.get_published(db, module_id)
    except service.TrainingError as exc:
        raise _http(exc) from None
    return service.module_out(module, service.enrollment_for(db, user, module.id))


@router.post(
    "/modules/{module_id}/enroll", response_model=ModuleOut, status_code=status.HTTP_201_CREATED
)
def enroll(
    module_id: uuid.UUID,
    response: Response,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    """Enrol in a free module, or reserve a paid one (which stays locked: no payment gateway)."""
    try:
        enrollment, created = service.enroll(db, user, module_id)
    except service.TrainingError as exc:
        raise _http(exc) from None
    if not created:
        response.status_code = status.HTTP_200_OK
    return service.module_out(service.get_published(db, module_id), enrollment)


@router.put("/modules/{module_id}/lessons/{index}", response_model=ModuleOut)
def lesson_progress(
    module_id: uuid.UUID,
    index: int,
    data: LessonProgressIn,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    try:
        enrollment = service.complete_lesson(db, user, module_id, index, data.done)
    except service.TrainingError as exc:
        raise _http(exc) from None
    return service.module_out(service.get_published(db, module_id), enrollment)
