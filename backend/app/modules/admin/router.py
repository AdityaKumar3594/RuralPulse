import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.db import get_db
from app.modules.facilitator.models import FacilitatorAssignment
from app.modules.identity import service as identity
from app.modules.identity.deps import require_role
from app.modules.identity.models import Role, User
from app.modules.identity.schemas import Name, Phone
from app.modules.partners import service as partners
from app.modules.partners.models import Provider, ProviderStatus, SubmissionStatus
from app.modules.partners.schemas import (
    DecisionIn,
    DecisionOut,
    EvidenceIn,
    ProviderOut,
    SubmissionOut,
)
from app.modules.sources.seed_schema import VerifiedField

router = APIRouter(prefix="/admin", tags=["admin"])
require_admin = require_role(Role.ADMIN)


class StaffIn(BaseModel):
    role: Literal["facilitator", "partner"]  # administrators are created from the command line
    phone: Phone
    pin: str = Field(pattern=r"^\d{6,12}$")
    display_name: Name


class UserOut(BaseModel):
    id: uuid.UUID
    role: str
    display_name: str
    phone: str
    is_active: bool


class AssignmentIn(BaseModel):
    facilitator_id: uuid.UUID
    student_id: uuid.UUID


class AssignmentOut(BaseModel):
    id: uuid.UUID
    facilitator_id: uuid.UUID
    student_id: uuid.UUID
    created_at: datetime
    ended_at: datetime | None


class ReverifyIn(BaseModel):
    verified_fields: list[VerifiedField]
    evidence: list[EvidenceIn]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_staff(
    data: StaffIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    try:
        return identity.create_staff_user(
            db, Role(data.role), data.phone, data.pin, data.display_name, admin.id
        )
    except identity.PhoneAlreadyRegistered:
        raise HTTPException(status.HTTP_409_CONFLICT, "phone_already_registered") from None


@router.get("/users", response_model=list[UserOut])
def list_users(
    role: Role | None = None, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    stmt = select(User).order_by(User.created_at.desc()).limit(500)
    if role:
        stmt = stmt.where(User.role == role)
    return list(db.scalars(stmt))


@router.post("/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def assign(data: AssignmentIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    facilitator, student = db.get(User, data.facilitator_id), db.get(User, data.student_id)
    if (
        facilitator is None
        or student is None
        or facilitator.role is not Role.FACILITATOR
        or student.role is not Role.STUDENT
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_assignment")
    active = db.scalar(
        select(FacilitatorAssignment).where(
            FacilitatorAssignment.facilitator_id == facilitator.id,
            FacilitatorAssignment.student_id == student.id,
            FacilitatorAssignment.ended_at.is_(None),
        )
    )
    if active is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "already_assigned")
    row = FacilitatorAssignment(
        facilitator_id=facilitator.id, student_id=student.id, assigned_by=admin.id
    )
    db.add(row)
    audit(
        db,
        "assignment.created",
        actor_id=admin.id,
        subject_user_id=student.id,
        facilitator=str(facilitator.id),
    )
    db.commit()
    return row


@router.get("/assignments", response_model=list[AssignmentOut])
def list_assignments(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return list(
        db.scalars(select(FacilitatorAssignment).order_by(FacilitatorAssignment.created_at.desc()))
    )


@router.delete("/assignments/{assignment_id}", response_model=AssignmentOut)
def end_assignment(
    assignment_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    row = db.get(FacilitatorAssignment, assignment_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    if row.ended_at is None:
        row.ended_at = datetime.now(UTC)
        audit(db, "assignment.ended", actor_id=admin.id, subject_user_id=row.student_id)
        db.commit()
    return row


@router.get("/providers", response_model=list[ProviderOut])
def list_providers(
    status_: ProviderStatus | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(Provider).order_by(Provider.created_at)
    if status_:
        stmt = stmt.where(Provider.status == status_)
    return list(db.scalars(stmt))


@router.post("/providers/{provider_id}/approve", response_model=ProviderOut)
def approve_provider(
    provider_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    try:
        return partners.set_provider_status(db, admin, provider_id, True)
    except partners.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found") from None
    except partners.InvalidInput as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.code) from None


@router.post("/providers/{provider_id}/suspend", response_model=ProviderOut)
def suspend_provider(
    provider_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    try:
        return partners.set_provider_status(db, admin, provider_id, False)
    except partners.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found") from None


@router.get("/submissions", response_model=list[SubmissionOut])
def review_queue(
    status_: SubmissionStatus | None = SubmissionStatus.SUBMITTED,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return partners.queue(db, status_)


@router.post("/submissions/{submission_id}/decision", response_model=DecisionOut)
def decide(
    submission_id: uuid.UUID,
    data: DecisionIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve (publishing only what you verified, with evidence), request changes, or reject."""
    try:
        submission, opp, stripped = partners.decide(db, admin, submission_id, data)
    except partners.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found") from None
    except partners.InvalidState as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    except partners.InvalidInput as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.code) from None
    return DecisionOut(
        submission=SubmissionOut.model_validate(submission, from_attributes=True),
        published_slug=opp.slug if opp else None,
        verification_status=opp.verification_status.value if opp else None,
        stripped_claims=stripped,
    )


@router.post("/submissions/{submission_id}/withdraw", response_model=SubmissionOut)
def withdraw_submission(
    submission_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    try:
        return partners.withdraw(db, admin, submission_id, as_admin=True)
    except partners.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found") from None
    except partners.InvalidState as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None


@router.post("/opportunities/{slug}/withdraw", status_code=status.HTTP_204_NO_CONTENT)
def withdraw_opportunity(
    slug: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    try:
        partners.withdraw_opportunity(db, admin, slug)
    except partners.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found") from None


@router.post("/opportunities/{slug}/reverify", status_code=status.HTTP_204_NO_CONTENT)
def reverify_opportunity(
    slug: str, data: ReverifyIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Record that a person re-checked the record against its official page today."""
    try:
        partners.reverify_opportunity(
            db, admin, slug, list(data.verified_fields), [e.model_dump() for e in data.evidence]
        )
    except partners.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found") from None
    except partners.InvalidInput as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.code) from None
