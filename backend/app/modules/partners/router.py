import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity.deps import require_role
from app.modules.identity.models import Role, User
from app.modules.partners import service
from app.modules.partners.schemas import (
    ConfirmIn,
    ConfirmOut,
    ProviderIn,
    ProviderOut,
    ProviderUpdate,
    StatsOut,
    SubmissionOut,
    SubmissionPayload,
)

router = APIRouter(prefix="/partner", tags=["partners"])
require_partner = require_role(Role.PARTNER)


def _errors(exc: Exception) -> HTTPException:
    if isinstance(exc, service.NotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    if isinstance(exc, service.Forbidden):
        return HTTPException(status.HTTP_403_FORBIDDEN, "not_allowed")
    if isinstance(exc, service.InvalidInput):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.code)
    if isinstance(exc, service.InvalidState):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    raise exc


@router.post("/provider", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
def create_provider(
    data: ProviderIn, user: User = Depends(require_partner), db: Session = Depends(get_db)
):
    try:
        return service.create_provider(db, user, data)
    except service.PartnerError as exc:
        raise _errors(exc) from None


@router.get("/provider", response_model=ProviderOut)
def get_provider(user: User = Depends(require_partner), db: Session = Depends(get_db)):
    provider = service.provider_for(db, user)
    if provider is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    return provider


@router.put("/provider", response_model=ProviderOut)
def update_provider(
    data: ProviderUpdate, user: User = Depends(require_partner), db: Session = Depends(get_db)
):
    try:
        return service.update_provider(db, user, data.model_dump(exclude_unset=True))
    except service.PartnerError as exc:
        raise _errors(exc) from None


@router.post("/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(
    data: SubmissionPayload, user: User = Depends(require_partner), db: Session = Depends(get_db)
):
    try:
        return service.create_submission(db, user, data)
    except service.PartnerError as exc:
        raise _errors(exc) from None


@router.get("/submissions", response_model=list[SubmissionOut])
def list_submissions(user: User = Depends(require_partner), db: Session = Depends(get_db)):
    return service.list_submissions(db, user)


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: uuid.UUID, user: User = Depends(require_partner), db: Session = Depends(get_db)
):
    try:
        return service.get_submission(db, user, submission_id)
    except service.PartnerError as exc:
        raise _errors(exc) from None


@router.put("/submissions/{submission_id}", response_model=SubmissionOut)
def update_submission(
    submission_id: uuid.UUID,
    data: SubmissionPayload,
    user: User = Depends(require_partner),
    db: Session = Depends(get_db),
):
    try:
        return service.update_submission(db, user, submission_id, data)
    except service.PartnerError as exc:
        raise _errors(exc) from None


@router.post("/submissions/{submission_id}/submit", response_model=SubmissionOut)
def submit(
    submission_id: uuid.UUID, user: User = Depends(require_partner), db: Session = Depends(get_db)
):
    try:
        return service.submit(db, user, submission_id)
    except service.PartnerError as exc:
        raise _errors(exc) from None


@router.post("/submissions/{submission_id}/withdraw", response_model=SubmissionOut)
def withdraw(
    submission_id: uuid.UUID, user: User = Depends(require_partner), db: Session = Depends(get_db)
):
    try:
        return service.withdraw(db, user, submission_id)
    except service.PartnerError as exc:
        raise _errors(exc) from None


@router.post(
    "/submissions/{submission_id}/revise",
    response_model=SubmissionOut,
    status_code=status.HTTP_201_CREATED,
)
def revise(
    submission_id: uuid.UUID, user: User = Depends(require_partner), db: Session = Depends(get_db)
):
    try:
        return service.revise(db, user, submission_id)
    except service.PartnerError as exc:
        raise _errors(exc) from None


@router.post("/applications/confirm", response_model=ConfirmOut)
def confirm_application(
    data: ConfirmIn, user: User = Depends(require_partner), db: Session = Depends(get_db)
):
    """Confirm what happened to an application, identified only by the code the student shared."""
    try:
        app = service.confirm_application(db, user, data.reference_code, data.status, data.note)
    except service.PartnerError as exc:
        raise _errors(exc) from None
    return ConfirmOut(opportunity=app.opportunity_slug, external_status=app.external_status.value)


@router.get("/opportunities/{slug}/stats", response_model=StatsOut)
def opportunity_stats(
    slug: str, user: User = Depends(require_partner), db: Session = Depends(get_db)
):
    try:
        data = service.stats(db, user, slug)
    except service.PartnerError as exc:
        raise _errors(exc) from None
    return StatsOut(opportunity=slug, **data)
