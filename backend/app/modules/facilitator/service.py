import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.modules.applications.models import Application
from app.modules.facilitator.models import (
    Endorsement,
    EndorsementStatus,
    FacilitatorAssignment,
    HelpRequest,
    HelpStatus,
    RecommendationReview,
    ReviewDecision,
)
from app.modules.identity import service as identity
from app.modules.identity.models import User
from app.modules.profile import service as profile_service
from app.modules.profile.models import Provenance, Verification
from app.modules.recommend import service as recommend_service
from app.modules.sources.models import Opportunity, Publication


class FacilitatorError(Exception):
    pass


class NotFound(FacilitatorError):
    """Unknown student, or not assigned to this facilitator. Deliberately indistinguishable."""


class NotShared(FacilitatorError):
    """The student (or guardian) has not agreed to share their profile with facilitators."""


class Conflict(FacilitatorError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def assigned_students(db: Session, facilitator: User) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .join(FacilitatorAssignment, FacilitatorAssignment.student_id == User.id)
            .where(
                FacilitatorAssignment.facilitator_id == facilitator.id,
                FacilitatorAssignment.ended_at.is_(None),
            )
            .order_by(User.display_name)
        )
    )


def shared(db: Session, student: User) -> bool:
    return identity.has_valid_consent(db, student, identity.FACILITATOR_ACCESS)


def authorize(
    db: Session, facilitator: User, student_id: uuid.UUID, need_share: bool = True
) -> User:
    """The one gate for every facilitator action on a student. Server-side, every time."""
    assignment = db.scalar(
        select(FacilitatorAssignment).where(
            FacilitatorAssignment.facilitator_id == facilitator.id,
            FacilitatorAssignment.student_id == student_id,
            FacilitatorAssignment.ended_at.is_(None),
        )
    )
    student = db.get(User, student_id)
    if assignment is None or student is None:
        raise NotFound
    if need_share and not shared(db, student):
        raise NotShared
    return student


def dashboard(db: Session, facilitator: User) -> list[dict[str, Any]]:
    out = []
    for student in assigned_students(db, facilitator):
        open_requests = db.scalar(
            select(func.count())
            .select_from(HelpRequest)
            .where(HelpRequest.student_id == student.id, HelpRequest.status == HelpStatus.OPEN)
        )
        is_shared = shared(db, student)
        out.append(
            {
                "id": student.id,
                "display_name": student.display_name,
                "preferred_language": student.preferred_language,
                "is_minor": identity.is_minor(student),
                "shared": is_shared,
                # Help requests are the student reaching out, so they are visible even before
                # the student shares their whole profile.
                "open_help_requests": open_requests,
            }
        )
    return out


def profile_for(db: Session, facilitator: User, student_id: uuid.UUID) -> tuple[User, list[dict]]:
    student = authorize(db, facilitator, student_id)
    audit(db, "facilitator.viewed_profile", actor_id=facilitator.id, subject_user_id=student.id)
    db.commit()
    return student, profile_service.build_view(profile_service.current_entries(db, student.id))


def record(
    db: Session,
    facilitator: User,
    student_id: uuid.UUID,
    key: str,
    value: Any,
    provenance: Provenance,
    basis: str | None,
    verified: bool = False,
) -> None:
    """Observed/hypothesis entries (with a written basis) or assisted self-reports. They live in
    their own provenance slots, so they never overwrite what the student reported."""
    student = authorize(db, facilitator, student_id)
    if provenance is Provenance.REPORTED or provenance is Provenance.UNKNOWN:
        source = f"assisted_by:{facilitator.id}"  # the student told the facilitator
    else:
        source = f"facilitator:{facilitator.id}"
    profile_service.record_entry(
        db,
        user_id=student.id,
        key=key,
        value=value,
        provenance=provenance,
        source=source,
        recorded_by=facilitator.id,
        basis=basis,
        verification=Verification.VERIFIED if verified else Verification.UNVERIFIED,
    )


def latest_recommendations(
    db: Session, facilitator: User, student_id: uuid.UUID, lang: str, fresh_days: int
) -> dict[str, Any] | None:
    student = authorize(db, facilitator, student_id)
    run = recommend_service.latest_run(db, student)
    audit(
        db,
        "facilitator.viewed_recommendations",
        actor_id=facilitator.id,
        subject_user_id=student.id,
    )
    db.commit()
    return recommend_service.run_out(db, run, lang, fresh_days) if run else None


def review_recommendation(
    db: Session,
    facilitator: User,
    student_id: uuid.UUID,
    run_id: uuid.UUID,
    career: str,
    decision: ReviewDecision,
    note: str | None,
) -> RecommendationReview:
    student = authorize(db, facilitator, student_id)
    run = db.get(recommend_service.RecommendationRun, run_id)
    if (
        run is None
        or run.user_id != student.id
        or not any(r["slug"] == career for r in run.results)
    ):
        raise NotFound
    review = RecommendationReview(
        facilitator_id=facilitator.id,
        student_id=student.id,
        run_id=run.id,
        career_slug=career,
        decision=decision,
        note=note,
    )
    db.add(review)
    audit(
        db,
        "facilitator.reviewed_recommendation",
        actor_id=facilitator.id,
        subject_user_id=student.id,
    )
    db.commit()
    return review


def endorse(
    db: Session, facilitator: User, student_id: uuid.UUID, slug: str, note: str | None
) -> Endorsement:
    student = authorize(db, facilitator, student_id)
    opp = db.get(Opportunity, slug)
    if opp is None or opp.publication_status is not Publication.PUBLISHED:
        raise NotFound
    row = Endorsement(
        facilitator_id=facilitator.id, student_id=student.id, opportunity_slug=slug, note=note
    )
    db.add(row)
    audit(
        db,
        "facilitator.endorsed",
        actor_id=facilitator.id,
        subject_user_id=student.id,
        opportunity=slug,
    )
    db.commit()
    return row


def student_applications(
    db: Session, facilitator: User, student_id: uuid.UUID
) -> list[Application]:
    student = authorize(db, facilitator, student_id)
    return list(
        db.scalars(
            select(Application)
            .where(Application.user_id == student.id)
            .order_by(Application.updated_at.desc())
        )
    )


def application_for_confirm(
    db: Session, facilitator: User, application_id: uuid.UUID
) -> Application:
    app = db.get(Application, application_id)
    if app is None:
        raise NotFound
    authorize(db, facilitator, app.user_id)
    return app


def open_help_requests(db: Session, facilitator: User) -> list[HelpRequest]:
    ids = [s.id for s in assigned_students(db, facilitator)]
    if not ids:
        return []
    return list(
        db.scalars(
            select(HelpRequest)
            .where(HelpRequest.student_id.in_(ids), HelpRequest.status == HelpStatus.OPEN)
            .order_by(HelpRequest.created_at)
        )
    )


def resolve_help(db: Session, facilitator: User, request_id: uuid.UUID) -> HelpRequest:
    req = db.get(HelpRequest, request_id)
    if req is None:
        raise NotFound
    authorize(db, facilitator, req.student_id, need_share=False)
    req.status = HelpStatus.RESOLVED
    req.resolved_by = facilitator.id
    req.resolved_at = datetime.now(UTC)
    audit(db, "help.resolved", actor_id=facilitator.id, subject_user_id=req.student_id)
    db.commit()
    return req


# --- the student's side -------------------------------------------------------------------------


def my_facilitators(db: Session, student: User) -> list[dict[str, Any]]:
    rows = db.execute(
        select(User, FacilitatorAssignment)
        .join(FacilitatorAssignment, FacilitatorAssignment.facilitator_id == User.id)
        .where(
            FacilitatorAssignment.student_id == student.id, FacilitatorAssignment.ended_at.is_(None)
        )
    )
    return [{"id": u.id, "display_name": u.display_name, "since": a.created_at} for u, a in rows]


def my_endorsements(db: Session, student: User) -> list[Endorsement]:
    return list(
        db.scalars(
            select(Endorsement)
            .where(Endorsement.student_id == student.id)
            .order_by(Endorsement.created_at.desc())
        )
    )


def set_endorsement_status(
    db: Session, student: User, endorsement_id: uuid.UUID, status: EndorsementStatus
) -> Endorsement:
    row = db.get(Endorsement, endorsement_id)
    if row is None or row.student_id != student.id:
        raise NotFound
    row.status = status
    db.commit()
    return row
