import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.applications import service
from app.modules.applications.schemas import (
    ApplicationOut,
    HelpIn,
    SaveRequest,
    UpdateRequest,
)
from app.modules.identity.deps import require_student_with_consent
from app.modules.identity.models import User

router = APIRouter(prefix="/applications", tags=["applications"])
Lang = Query(default="en", pattern="^(ta|en)$")


def _days(request: Request) -> int:
    return request.app.state.settings.source_fresh_days


def _http(exc: service.ApplicationError) -> HTTPException:
    if isinstance(exc, service.Conflict):
        return HTTPException(status.HTTP_409_CONFLICT, exc.code)
    return HTTPException(status.HTTP_404_NOT_FOUND, "not_found")


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def save(
    data: SaveRequest,
    request: Request,
    response: Response,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    """Save an opportunity to track. Tracking is ours; it does not apply on the student's behalf."""
    try:
        app, created = service.save(db, user, data.opportunity)
    except service.ApplicationError as exc:
        raise _http(exc) from None
    if not created:
        response.status_code = status.HTTP_200_OK
    return service.application_out(db, app, data.language, _days(request))


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    request: Request,
    language: Literal["ta", "en"] = Lang,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    return [
        service.application_out(db, a, language, _days(request)) for a in service.list_own(db, user)
    ]


@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: uuid.UUID,
    request: Request,
    language: Literal["ta", "en"] = Lang,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    try:
        app = service.get_own(db, user, application_id)
    except service.ApplicationError as exc:
        raise _http(exc) from None
    return service.application_out(db, app, language, _days(request))


@router.put("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: uuid.UUID,
    data: UpdateRequest,
    request: Request,
    language: Literal["ta", "en"] = Lang,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    try:
        app = service.update(
            db,
            user,
            application_id,
            data.internal_status,
            data.note,
            data.documents,
            data.reported_external_status,
        )
    except service.ApplicationError as exc:
        raise _http(exc) from None
    return service.application_out(db, app, language, _days(request))


@router.post("/{application_id}/help", status_code=status.HTTP_201_CREATED)
def ask_for_help(
    application_id: uuid.UUID,
    data: HelpIn,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    """Ask a facilitator for help with this application."""
    try:
        app = service.get_own(db, user, application_id)
    except service.ApplicationError as exc:
        raise _http(exc) from None
    req = service.request_help(db, user, app, data.message)
    return {"id": str(req.id), "status": req.status.value}
