import re
import uuid
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.ingestion.loader import build_search_text
from app.modules.applications.models import (
    Application,
    ExternalStatus,
    StatusSource,
)
from app.modules.identity.models import User
from app.modules.partners.models import (
    OpportunitySubmission,
    Provider,
    ProviderMember,
    ProviderStatus,
    SubmissionStatus,
)
from app.modules.partners.schemas import DecisionIn, ProviderIn, SubmissionPayload
from app.modules.sources.models import Opportunity, Publication, Source, Verification
from app.modules.sources.seed_schema import (
    TRUSTED_SUFFIXES,
    OpportunitySeed,
    host_allowed,
    https_host,
)

EDITABLE = (SubmissionStatus.DRAFT, SubmissionStatus.CHANGES_REQUESTED)
CLAIM_FIELD = {  # verified field name -> how to tell the claim is present in the payload
    "eligibility": lambda p: p.eligibility is not None,
    "benefit": lambda p: bool(p.benefits),
    "deadline": lambda p: p.application_deadline is not None,
    "documents": lambda p: bool(p.required_documents),
    "scope": lambda p: p.scope.level == "state",
}


class PartnerError(Exception):
    pass


class NotFound(PartnerError):
    pass


class Forbidden(PartnerError):
    pass


class InvalidState(PartnerError):
    pass


class InvalidInput(PartnerError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _host(url: str) -> str:
    try:
        return https_host(url)
    except ValueError:
        raise InvalidInput("url_must_be_https") from None


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


# --- provider profile ---


def provider_for(db: Session, user: User) -> Provider | None:
    return db.scalar(select(Provider).join(ProviderMember).where(ProviderMember.user_id == user.id))


def create_provider(db: Session, user: User, data: ProviderIn) -> Provider:
    if provider_for(db, user) is not None:
        raise InvalidState("already_has_provider")
    _host(data.website)
    provider = Provider(
        name=data.name,
        kind=data.kind,
        website=data.website,
        description=data.description,
        created_by=user.id,
    )
    db.add(provider)
    db.flush()
    db.add(ProviderMember(provider_id=provider.id, user_id=user.id))
    audit(db, "provider.created", actor_id=user.id, provider=str(provider.id))
    db.commit()
    return provider


def update_provider(db: Session, user: User, changes: dict[str, Any]) -> Provider:
    provider = provider_for(db, user)
    if provider is None:
        raise NotFound
    identity = {"name", "kind", "website"} & changes.keys()
    if identity and provider.status is not ProviderStatus.PENDING:
        # Who the provider is was approved; changing it needs a fresh review.
        raise InvalidState("identity_locked_after_approval")
    if "website" in changes:
        _host(changes["website"])
    for key, value in changes.items():
        setattr(provider, key, value)
    db.commit()
    return provider


def set_provider_status(
    db: Session, admin: User, provider_id: uuid.UUID, approve: bool
) -> Provider:
    provider = db.get(Provider, provider_id)
    if provider is None:
        raise NotFound
    if approve:
        provider.status = ProviderStatus.APPROVED
        provider.approved_by, provider.approved_at = admin.id, datetime.now(UTC)
        if provider.source_id is None:
            host = _host(provider.website)
            source = Source(
                id=f"provider-{provider.id.hex[:12]}",
                name={"en": provider.name},
                publisher=provider.name,
                base_url=provider.website,
                category="partner_provider",
                allowed_domains=[host],
                api_access="unknown",
            )
            db.add(source)
            db.flush()
            provider.source_id = source.id
    else:
        provider.status = ProviderStatus.SUSPENDED
        # A suspended provider's published opportunities disappear from search.
        for opp in db.scalars(
            select(Opportunity).where(Opportunity.source_id == provider.source_id)
        ):
            opp.publication_status = Publication.WITHDRAWN
    audit(
        db,
        "provider.approved" if approve else "provider.suspended",
        actor_id=admin.id,
        provider=str(provider.id),
    )
    db.commit()
    return provider


# --- submissions ---


def _own(
    db: Session, user: User, submission_id: uuid.UUID
) -> tuple[OpportunitySubmission, Provider]:
    provider = provider_for(db, user)
    submission = db.get(OpportunitySubmission, submission_id)
    if provider is None or submission is None or submission.provider_id != provider.id:
        raise NotFound
    return submission, provider


def create_submission(
    db: Session, user: User, payload: SubmissionPayload, replaces_slug: str | None = None
) -> OpportunitySubmission:
    provider = provider_for(db, user)
    if provider is None:
        raise NotFound
    if provider.status is not ProviderStatus.APPROVED:
        raise InvalidState("provider_not_approved")
    submission = OpportunitySubmission(
        provider_id=provider.id,
        submitted_by=user.id,
        payload=payload.model_dump(mode="json"),
        replaces_slug=replaces_slug,
    )
    db.add(submission)
    audit(db, "submission.created", actor_id=user.id, provider=str(provider.id))
    db.commit()
    return submission


def update_submission(
    db: Session, user: User, submission_id: uuid.UUID, payload: SubmissionPayload
) -> OpportunitySubmission:
    submission, _ = _own(db, user, submission_id)
    if submission.status not in EDITABLE:
        raise InvalidState("not_editable")
    submission.payload = payload.model_dump(mode="json")
    submission.revision += 1
    db.commit()
    return submission


def list_submissions(db: Session, user: User) -> list[OpportunitySubmission]:
    provider = provider_for(db, user)
    if provider is None:
        return []
    return list(
        db.scalars(
            select(OpportunitySubmission)
            .where(OpportunitySubmission.provider_id == provider.id)
            .order_by(OpportunitySubmission.created_at.desc())
        )
    )


def get_submission(db: Session, user: User, submission_id: uuid.UUID) -> OpportunitySubmission:
    return _own(db, user, submission_id)[0]


def submit(db: Session, user: User, submission_id: uuid.UUID) -> OpportunitySubmission:
    submission, provider = _own(db, user, submission_id)
    if submission.status not in EDITABLE:
        raise InvalidState("not_editable")
    payload = SubmissionPayload.model_validate(submission.payload)
    if not host_allowed(_host(payload.url), [urlparse(provider.website).hostname or ""]):
        raise InvalidInput("url_must_be_on_provider_website")
    submission.status = SubmissionStatus.SUBMITTED
    audit(db, "submission.submitted", actor_id=user.id, submission=str(submission.id))
    db.commit()
    return submission


def withdraw(db: Session, actor: User, submission_id: uuid.UUID, as_admin: bool = False):
    if as_admin:
        submission = db.get(OpportunitySubmission, submission_id)
        if submission is None:
            raise NotFound
    else:
        submission, _ = _own(db, actor, submission_id)
    if submission.status in (SubmissionStatus.REJECTED, SubmissionStatus.WITHDRAWN):
        raise InvalidState("already_closed")
    if submission.published_slug:  # taking it back also takes the published listing down
        opp = db.get(Opportunity, submission.published_slug)
        if opp is not None:
            opp.publication_status = Publication.WITHDRAWN
    submission.status = SubmissionStatus.WITHDRAWN
    audit(db, "submission.withdrawn", actor_id=actor.id, submission=str(submission.id))
    db.commit()
    return submission


def revise(db: Session, user: User, submission_id: uuid.UUID) -> OpportunitySubmission:
    """Start a new draft from a published submission. The live listing is untouched until the
    new draft is submitted and approved."""
    old, provider = _own(db, user, submission_id)
    if old.status is not SubmissionStatus.APPROVED or not old.published_slug:
        raise InvalidState("only_published_can_be_revised")
    draft = OpportunitySubmission(
        provider_id=provider.id,
        submitted_by=user.id,
        payload=dict(old.payload),
        replaces_slug=old.published_slug,
    )
    db.add(draft)
    audit(db, "submission.revision_started", actor_id=user.id, replaces=old.published_slug)
    db.commit()
    return draft


# --- review (administrator) ---


def queue(db: Session, status: SubmissionStatus | None) -> list[OpportunitySubmission]:
    stmt = select(OpportunitySubmission).order_by(OpportunitySubmission.updated_at)
    if status:
        stmt = stmt.where(OpportunitySubmission.status == status)
    return list(db.scalars(stmt))


def _check_evidence(provider: Provider, evidence: list[dict[str, str]]) -> None:
    provider_host = urlparse(provider.website).hostname or ""
    for ev in evidence:
        host = _host(ev["url"])
        if not (host.endswith(TRUSTED_SUFFIXES) or host_allowed(host, [provider_host])):
            raise InvalidInput("evidence_must_be_official_or_on_provider_site")


def decide(
    db: Session, admin: User, submission_id: uuid.UUID, decision: DecisionIn
) -> tuple[OpportunitySubmission, Opportunity | None, list[str]]:
    submission = db.get(OpportunitySubmission, submission_id)
    if submission is None:
        raise NotFound
    if submission.status is not SubmissionStatus.SUBMITTED:
        raise InvalidState("not_awaiting_review")
    provider = db.get(Provider, submission.provider_id)
    submission.reviewed_by, submission.reviewed_at = admin.id, datetime.now(UTC)
    submission.review_notes = decision.notes
    if decision.decision == "reject":
        submission.status = SubmissionStatus.REJECTED
        audit(db, "submission.rejected", actor_id=admin.id, submission=str(submission.id))
        db.commit()
        return submission, None, []
    if decision.decision == "request_changes":
        if not decision.notes:
            raise InvalidInput("notes_required")
        submission.status = SubmissionStatus.CHANGES_REQUESTED
        audit(db, "submission.changes_requested", actor_id=admin.id, submission=str(submission.id))
        db.commit()
        return submission, None, []

    # Approve: publish, and verify exactly what the administrator vouches for.
    if provider.status is not ProviderStatus.APPROVED or provider.source_id is None:
        raise InvalidState("provider_not_approved")
    payload = SubmissionPayload.model_validate(submission.payload)
    verified = list(dict.fromkeys(decision.verification.verified_fields))
    evidence = [e.model_dump() for e in decision.verification.evidence]
    if verified and not evidence:
        raise InvalidInput("evidence_required")
    for name in verified:
        if name in CLAIM_FIELD and not CLAIM_FIELD[name](payload):
            raise InvalidInput(f"cannot_verify_absent_claim:{name}")
    _check_evidence(provider, evidence)
    stripped = [
        name for name, present in CLAIM_FIELD.items() if present(payload) and name not in verified
    ]

    slug = submission.replaces_slug or (
        f"{slugify(provider.name)[:24]}-{slugify(payload.title['en'])[:30]}-{submission.id.hex[:6]}"
    )
    try:
        seed = OpportunitySeed.model_validate(
            {
                "slug": slug.strip("-"),
                "source": provider.source_id,
                "kind": payload.kind,
                "title": payload.title,
                "summary": payload.summary,
                "provider": provider.name,
                "url": payload.url,
                "keywords": payload.keywords,
                "scope": payload.scope.model_dump() if "scope" in verified else {},
                "eligibility": payload.eligibility.model_dump(mode="json")
                if "eligibility" in verified and payload.eligibility
                else None,
                "required_documents": payload.required_documents if "documents" in verified else [],
                "application_deadline": payload.application_deadline
                if "deadline" in verified
                else None,
                "expires_on": payload.expires_on,
                "benefits": [b.model_dump(mode="json") for b in payload.benefits]
                if "benefit" in verified
                else [],
                "verification": {
                    "status": "verified" if verified else "unverified",
                    "verified_fields": verified,
                    "verified_at": date.today() if verified else None,
                    "verified_by": f"admin:{admin.id}" if verified else None,
                    "human_reviewed": bool(verified),  # a person reviewed it
                    "evidence": evidence if verified else [],
                },
            }
        )
    except ValidationError as exc:
        raise InvalidInput("submission_failed_validation") from exc

    opp = db.get(Opportunity, seed.slug) or Opportunity(slug=seed.slug)
    v = seed.verification
    opp.source_id, opp.kind, opp.title, opp.summary = (
        provider.source_id,
        seed.kind,
        seed.title,
        seed.summary,
    )
    opp.provider, opp.url, opp.keywords = provider.name, seed.url, seed.keywords
    opp.scope = seed.scope.model_dump(mode="json")
    opp.eligibility = seed.eligibility.model_dump(mode="json") if seed.eligibility else None
    opp.required_documents = seed.required_documents
    opp.application_deadline, opp.expires_on = seed.application_deadline, seed.expires_on
    opp.benefits = [b.model_dump(mode="json") for b in seed.benefits]
    opp.verification_status = Verification(v.status)
    opp.verified_fields, opp.verified_at, opp.verified_by = (
        list(v.verified_fields),
        v.verified_at,
        v.verified_by,
    )
    opp.human_reviewed = v.human_reviewed
    opp.evidence = [e.model_dump() for e in v.evidence]
    opp.publication_status = Publication.PUBLISHED
    opp.retrieved_at = datetime.now(UTC)
    opp.search_text = build_search_text(seed.title, seed.summary, provider.name, seed.keywords)
    db.add(opp)
    db.flush()
    submission.status = SubmissionStatus.APPROVED
    submission.published_slug = opp.slug
    audit(
        db,
        "submission.approved",
        actor_id=admin.id,
        submission=str(submission.id),
        verified=verified,
        stripped=stripped,
    )
    db.commit()
    return submission, opp, stripped


def withdraw_opportunity(db: Session, admin: User, slug: str) -> Opportunity:
    opp = db.get(Opportunity, slug)
    if opp is None:
        raise NotFound
    opp.publication_status = Publication.WITHDRAWN
    audit(db, "opportunity.withdrawn", actor_id=admin.id, opportunity=slug)
    db.commit()
    return opp


def reverify_opportunity(
    db: Session, admin: User, slug: str, verified_fields: list[str], evidence: list[dict[str, str]]
) -> Opportunity:
    """A person re-checks an existing record against its official page. Can only re-confirm
    fields that are already present: it cannot add new structured claims."""
    opp = db.get(Opportunity, slug)
    if opp is None:
        raise NotFound
    if not evidence:
        raise InvalidInput("evidence_required")
    allowed = set(opp.verified_fields) | {"url", "provider", "existence"}
    if not set(verified_fields) <= allowed:
        raise InvalidInput("cannot_verify_new_claims")
    for ev in evidence:
        host = _host(ev["url"])
        source = db.get(Source, opp.source_id)
        if not (host.endswith(TRUSTED_SUFFIXES) or host_allowed(host, source.allowed_domains)):
            raise InvalidInput("evidence_must_be_official")
    opp.verified_fields = sorted(set(verified_fields) | set(opp.verified_fields))
    opp.verification_status = Verification.VERIFIED
    opp.verified_at = date.today()
    opp.verified_by = f"admin:{admin.id}"
    opp.human_reviewed = True
    opp.evidence = [*opp.evidence, *evidence]
    audit(db, "opportunity.reverified", actor_id=admin.id, opportunity=slug)
    db.commit()
    return opp


# --- provider confirms an application (by reference code only) ---


def confirm_application(
    db: Session, user: User, reference_code: str, status: str, note: str | None
) -> Application:
    provider = provider_for(db, user)
    if (
        provider is None
        or provider.source_id is None
        or provider.status is not ProviderStatus.APPROVED
    ):
        raise Forbidden
    app = db.scalar(select(Application).where(Application.reference_code == reference_code.upper()))
    opp = db.get(Opportunity, app.opportunity_slug) if app else None
    # Same answer whether the code is unknown or belongs to another provider: no probing.
    if app is None or opp is None or opp.source_id != provider.source_id:
        raise NotFound
    app.external_status = ExternalStatus(status)
    app.external_status_source = StatusSource.PROVIDER_CONFIRMED
    app.external_status_at = datetime.now(UTC)
    app.external_status_note = note
    app.external_status_by = user.id
    audit(
        db,
        "application.provider_confirmed",
        actor_id=user.id,
        subject_user_id=app.user_id,
        status=status,
    )
    db.commit()
    return app


def stats(db: Session, user: User, slug: str) -> dict[str, dict[str, int]]:
    """Aggregate counts only: a provider never sees who the students are."""
    provider = provider_for(db, user)
    opp = db.get(Opportunity, slug)
    if provider is None or opp is None or opp.source_id != provider.source_id:
        raise NotFound
    rows = db.scalars(select(Application).where(Application.opportunity_slug == slug))
    internal: dict[str, int] = {}
    external: dict[str, int] = {}
    for a in rows:
        internal[a.internal_status.value] = internal.get(a.internal_status.value, 0) + 1
        external[a.external_status.value] = external.get(a.external_status.value, 0) + 1
    return {"by_internal_status": internal, "by_external_status": external}
