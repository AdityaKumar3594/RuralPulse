import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.modules.applications.models import (
    CONFIRMED_SOURCES,
    Application,
    ExternalStatus,
    InternalStatus,
    StatusSource,
)
from app.modules.facilitator.models import HelpRequest, HelpTopic
from app.modules.identity.models import User
from app.modules.sources.models import Opportunity, Publication

S = InternalStatus
# Internal tracking only: what the student says they have done. Never proof of submission.
ALLOWED_TRANSITIONS: dict[InternalStatus, set[InternalStatus]] = {
    S.SAVED: {S.PREPARING, S.WITHDRAWN},
    S.PREPARING: {S.SAVED, S.DOCUMENTS_READY, S.APPLIED, S.WITHDRAWN},
    S.DOCUMENTS_READY: {S.PREPARING, S.APPLIED, S.WITHDRAWN},
    S.APPLIED: {S.WITHDRAWN},
    S.WITHDRAWN: {S.SAVED},
}


class ApplicationError(Exception):
    pass


class NotFound(ApplicationError):
    pass


class Conflict(ApplicationError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _published(db: Session, slug: str) -> Opportunity:
    opp = db.get(Opportunity, slug)
    if opp is None or opp.publication_status is not Publication.PUBLISHED:
        raise NotFound
    return opp


def save(db: Session, user: User, slug: str) -> tuple[Application, bool]:
    """Save an opportunity to track. Idempotent; saving a withdrawn one brings it back."""
    opp = _published(db, slug)
    app = db.scalar(
        select(Application).where(
            Application.user_id == user.id, Application.opportunity_slug == slug
        )
    )
    if app is None:
        app = Application(
            user_id=user.id,
            opportunity_slug=slug,
            documents={name: False for name in opp.required_documents},
        )
        db.add(app)
        audit(db, "application.saved", actor_id=user.id, subject_user_id=user.id, opportunity=slug)
        db.commit()
        return app, True
    if app.internal_status is S.WITHDRAWN:
        app.internal_status = S.SAVED
        db.commit()
    return app, False


def get_own(db: Session, user: User, application_id: uuid.UUID) -> Application:
    app = db.get(Application, application_id)
    if app is None or app.user_id != user.id:
        raise NotFound
    return app


def list_own(db: Session, user: User) -> list[Application]:
    return list(
        db.scalars(
            select(Application)
            .where(Application.user_id == user.id)
            .order_by(Application.updated_at.desc())
        )
    )


def update(
    db: Session,
    user: User,
    application_id: uuid.UUID,
    internal_status: InternalStatus | None,
    note: str | None,
    documents: dict[str, bool] | None,
    reported_external: ExternalStatus | None,
) -> Application:
    app = get_own(db, user, application_id)
    if documents is not None:
        if not set(documents) <= set(app.documents):
            raise Conflict("unknown_document")
        app.documents = {**app.documents, **documents}
    if note is not None:
        app.note = note
    if internal_status is not None and internal_status is not app.internal_status:
        if internal_status not in ALLOWED_TRANSITIONS[app.internal_status]:
            raise Conflict("invalid_transition")
        needs_documents = internal_status is S.DOCUMENTS_READY or (
            internal_status is S.APPLIED and app.internal_status is S.PREPARING and app.documents
        )
        if needs_documents and not all(app.documents.values()):
            raise Conflict("documents_not_ready")
        app.internal_status = internal_status
        audit(
            db,
            "application.status",
            actor_id=user.id,
            subject_user_id=user.id,
            status=internal_status.value,
        )
    if reported_external is not None:
        if app.internal_status is not S.APPLIED:
            raise Conflict("not_applied_yet")
        if app.external_status_source in CONFIRMED_SOURCES:
            raise Conflict("already_confirmed")  # a student's report never overrides a confirmation
        app.external_status = reported_external
        app.external_status_source = (
            StatusSource.STUDENT_REPORTED
            if reported_external is not ExternalStatus.UNKNOWN
            else None
        )
        app.external_status_at = datetime.now(UTC)
    db.commit()
    return app


def facilitator_confirm(
    db: Session, facilitator: User, app: Application, status: ExternalStatus, note: str | None
) -> Application:
    app.external_status = status
    app.external_status_source = StatusSource.FACILITATOR_CONFIRMED
    app.external_status_at = datetime.now(UTC)
    app.external_status_note = note
    app.external_status_by = facilitator.id
    audit(
        db,
        "application.facilitator_confirmed",
        actor_id=facilitator.id,
        subject_user_id=app.user_id,
        status=status.value,
    )
    db.commit()
    return app


def request_help(db: Session, user: User, app: Application, message: str | None) -> HelpRequest:
    req = HelpRequest(
        student_id=user.id,
        topic=HelpTopic.APPLICATION,
        message=message,
        opportunity_slug=app.opportunity_slug,
    )
    db.add(req)
    audit(db, "help.requested", actor_id=user.id, subject_user_id=user.id, topic="application")
    db.commit()
    return req


def application_out(db: Session, app: Application, lang: str, fresh_days: int) -> dict[str, Any]:
    from app.core.localize import Localizer
    from app.modules.sources.freshness import freshness

    opp = db.get(Opportunity, app.opportunity_slug)
    loc = Localizer(lang)
    confirmed = app.external_status_source in CONFIRMED_SOURCES
    return {
        "id": app.id,
        "opportunity": {
            "slug": opp.slug,
            "title": loc.text(opp.title),
            "url": opp.url,
            "kind": opp.kind,
            "freshness": freshness(opp, datetime.now(UTC).date(), fresh_days),
        },
        "internal_status": app.internal_status.value,
        "note": app.note,
        "documents": app.documents,
        "external_status": app.external_status.value,
        "external_status_source": app.external_status_source.value
        if app.external_status_source
        else None,
        "external_confirmed": confirmed and app.external_status is not ExternalStatus.UNKNOWN,
        "external_status_at": app.external_status_at,
        "external_status_note": app.external_status_note if confirmed else None,
        "reference_code": app.reference_code,
        "created_at": app.created_at,
        "updated_at": app.updated_at,
    }
