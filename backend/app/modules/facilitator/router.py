import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.applications import service as applications
from app.modules.applications.schemas import ApplicationOut
from app.modules.facilitator import service
from app.modules.facilitator.models import HelpRequest
from app.modules.facilitator.schemas import (
    AssistedAnswerIn,
    ConfirmIn,
    EndorseIn,
    EndorsementOut,
    EndorsementStatusIn,
    HelpRequestIn,
    HelpRequestOut,
    MyFacilitator,
    ObservationIn,
    ReviewIn,
    StudentProfileOut,
    StudentSummary,
)
from app.modules.identity.deps import require_role, require_student_with_consent
from app.modules.identity.models import Role, User
from app.modules.pathway import service as pathways
from app.modules.pathway.schemas import PlanOut, ProgressUpdate
from app.modules.profile import service as profile_service
from app.modules.profile.models import Provenance
from app.modules.recommend.schemas import RunOut

router = APIRouter(prefix="/facilitator", tags=["facilitator"])
student_router = APIRouter(prefix="/me", tags=["student"])
require_facilitator = require_role(Role.FACILITATOR)
Lang = Query(default="en", pattern="^(ta|en)$")


def _days(request: Request) -> int:
    return request.app.state.settings.source_fresh_days


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, service.NotShared):
        return HTTPException(status.HTTP_403_FORBIDDEN, "student_has_not_shared")
    if isinstance(exc, service.Conflict):
        return HTTPException(status.HTTP_409_CONFLICT, exc.code)
    return HTTPException(status.HTTP_404_NOT_FOUND, "not_found")


# --- facilitator -------------------------------------------------------------------------------


@router.get("/students", response_model=list[StudentSummary])
def list_students(facilitator: User = Depends(require_facilitator), db: Session = Depends(get_db)):
    """The students assigned to this facilitator, and whether each has shared their profile."""
    return service.dashboard(db, facilitator)


@router.get("/students/{student_id}/profile", response_model=StudentProfileOut)
def student_profile(
    student_id: uuid.UUID,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    try:
        student, view = service.profile_for(db, facilitator, student_id)
    except service.FacilitatorError as exc:
        raise _http(exc) from None
    summary = next(s for s in service.dashboard(db, facilitator) if s["id"] == student.id)
    fields = [
        {
            **{k: v for k, v in f.items() if k != "entries"},
            "entries": [
                {
                    "provenance": e.provenance.value,
                    "value": e.value,
                    "verification": e.verification.value,
                    "source": e.source,
                    "basis": e.basis,
                    "created_at": e.created_at.isoformat(),
                }
                for e in f["entries"]
            ],
        }
        for f in view
    ]
    return {"student": summary, "fields": fields}


@router.post("/students/{student_id}/observations", status_code=status.HTTP_201_CREATED)
def add_observation(
    student_id: uuid.UUID,
    data: ObservationIn,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    try:
        service.record(
            db,
            facilitator,
            student_id,
            data.key,
            data.value,
            Provenance(data.provenance),
            data.basis,
            data.verified,
        )
    except service.FacilitatorError as exc:
        raise _http(exc) from None
    except profile_service.UnknownField:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_field") from None
    except profile_service.InvalidValue:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_value") from None
    return {"recorded": data.key, "provenance": data.provenance}


@router.post("/students/{student_id}/assisted-answers", status_code=status.HTTP_201_CREATED)
def add_assisted_answer(
    student_id: uuid.UUID,
    data: AssistedAnswerIn,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    """Record an answer the student gave out loud during a facilitator-assisted interview."""
    try:
        service.record(
            db,
            facilitator,
            student_id,
            data.key,
            data.value,
            Provenance.UNKNOWN if data.unknown else Provenance.REPORTED,
            None,
        )
    except service.FacilitatorError as exc:
        raise _http(exc) from None
    except profile_service.UnknownField:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_field") from None
    except profile_service.InvalidValue:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_value") from None
    return {"recorded": data.key}


@router.get("/students/{student_id}/recommendations/latest", response_model=RunOut)
def student_recommendations(
    student_id: uuid.UUID,
    request: Request,
    language: Literal["ta", "en"] = Lang,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    try:
        out = service.latest_recommendations(db, facilitator, student_id, language, _days(request))
    except service.FacilitatorError as exc:
        raise _http(exc) from None
    if out is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no_recommendations_yet")
    return out


@router.post("/students/{student_id}/recommendations/review", status_code=status.HTTP_201_CREATED)
def review_recommendation(
    student_id: uuid.UUID,
    data: ReviewIn,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    try:
        review = service.review_recommendation(
            db, facilitator, student_id, data.run_id, data.career, data.decision, data.note
        )
    except service.FacilitatorError as exc:
        raise _http(exc) from None
    return {"id": str(review.id), "decision": review.decision.value}


@router.post("/students/{student_id}/endorsements", response_model=EndorsementOut, status_code=201)
def endorse(
    student_id: uuid.UUID,
    data: EndorseIn,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    """Suggest a published opportunity to a student you have spotted talent in."""
    try:
        return service.endorse(db, facilitator, student_id, data.opportunity, data.note)
    except service.FacilitatorError as exc:
        raise _http(exc) from None


@router.get("/students/{student_id}/pathways", response_model=list[PlanOut])
def student_pathways(
    student_id: uuid.UUID,
    request: Request,
    language: Literal["ta", "en"] = Lang,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    try:
        student = service.authorize(db, facilitator, student_id)
    except service.FacilitatorError as exc:
        raise _http(exc) from None
    return [
        pathways.plan_out(db, p, language, _days(request)) for p in pathways.list_plans(db, student)
    ]


@router.put("/students/{student_id}/pathways/{plan_id}/steps/{step_id}", response_model=PlanOut)
def support_pathway_step(
    student_id: uuid.UUID,
    plan_id: uuid.UUID,
    step_id: str,
    data: ProgressUpdate,
    request: Request,
    language: Literal["ta", "en"] = Lang,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    """Update a step on the student's behalf (the same prerequisite rules apply)."""
    try:
        student = service.authorize(db, facilitator, student_id)
        plan = pathways.get_plan(db, student, plan_id)
        pathways.set_progress(db, plan, step_id, data.status, data.note, facilitator.id)
    except service.FacilitatorError as exc:
        raise _http(exc) from None
    except pathways.PlanNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found") from None
    except pathways.UnknownStep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_step") from None
    except (pathways.PrerequisitesNotDone, pathways.DependentStepsStarted) as exc:
        code = (
            "prerequisites_not_done"
            if isinstance(exc, pathways.PrerequisitesNotDone)
            else "dependent_steps_started"
        )
        raise HTTPException(status.HTTP_409_CONFLICT, code) from None
    return pathways.plan_out(db, plan, language, _days(request))


@router.get("/students/{student_id}/applications", response_model=list[ApplicationOut])
def student_applications(
    student_id: uuid.UUID,
    request: Request,
    language: Literal["ta", "en"] = Lang,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    try:
        apps = service.student_applications(db, facilitator, student_id)
    except service.FacilitatorError as exc:
        raise _http(exc) from None
    return [applications.application_out(db, a, language, _days(request)) for a in apps]


@router.post("/applications/{application_id}/confirm", response_model=ApplicationOut)
def confirm_application(
    application_id: uuid.UUID,
    data: ConfirmIn,
    request: Request,
    language: Literal["ta", "en"] = Lang,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    """Confirm an external status you have seen evidence of (e.g. a provider acknowledgement)."""
    try:
        app = service.application_for_confirm(db, facilitator, application_id)
    except service.FacilitatorError as exc:
        raise _http(exc) from None
    app = applications.facilitator_confirm(db, facilitator, app, data.external(), data.note)
    return applications.application_out(db, app, language, _days(request))


@router.get("/help-requests", response_model=list[HelpRequestOut])
def help_requests(facilitator: User = Depends(require_facilitator), db: Session = Depends(get_db)):
    return service.open_help_requests(db, facilitator)


@router.post("/help-requests/{request_id}/resolve", response_model=HelpRequestOut)
def resolve_help(
    request_id: uuid.UUID,
    facilitator: User = Depends(require_facilitator),
    db: Session = Depends(get_db),
):
    try:
        return service.resolve_help(db, facilitator, request_id)
    except service.FacilitatorError as exc:
        raise _http(exc) from None


# --- the student's side ------------------------------------------------------------------------


@student_router.get("/facilitators", response_model=list[MyFacilitator])
def my_facilitators(
    user: User = Depends(require_student_with_consent), db: Session = Depends(get_db)
):
    """Who is assigned to help you (they only see your profile if you have shared it)."""
    return service.my_facilitators(db, user)


@student_router.get("/endorsements", response_model=list[EndorsementOut])
def my_endorsements(
    user: User = Depends(require_student_with_consent), db: Session = Depends(get_db)
):
    return service.my_endorsements(db, user)


@student_router.put("/endorsements/{endorsement_id}", response_model=EndorsementOut)
def update_endorsement(
    endorsement_id: uuid.UUID,
    data: EndorsementStatusIn,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    try:
        return service.set_endorsement_status(db, user, endorsement_id, data.value())
    except service.FacilitatorError as exc:
        raise _http(exc) from None


@student_router.post("/help-requests", response_model=HelpRequestOut, status_code=201)
def ask_for_help(
    data: HelpRequestIn,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    from app.core.audit import audit

    req = HelpRequest(student_id=user.id, topic=data.topic, message=data.message)
    db.add(req)
    audit(db, "help.requested", actor_id=user.id, subject_user_id=user.id, topic=data.topic.value)
    db.commit()
    return req
