"""Idempotent upsert of a validated SeedBundle. Never marks anything verified by itself:
verification comes only from what the seed record declares (and the schema already requires
evidence for that)."""

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ingestion.bundle import SeedBundle
from app.modules.catalog.models import Career
from app.modules.catalog.seed_schema import CareerSeed
from app.modules.sources.models import Opportunity, Publication, Source, Verification
from app.modules.sources.seed_schema import OpportunitySeed, SourceSeed


def build_search_text(*parts: object) -> str:
    """Flatten localized text and keywords into one lower-cased string for the search index."""
    out: list[str] = []

    def walk(p: object) -> None:
        if isinstance(p, dict):
            for v in p.values():
                walk(v)
        elif isinstance(p, (list, tuple)):
            for v in p:
                walk(v)
        elif p:
            out.append(str(p))

    for part in parts:
        walk(part)
    return " ".join(out).casefold()


def _source(s: SourceSeed) -> Source:
    return Source(
        id=s.id,
        name=s.name,
        publisher=s.publisher,
        base_url=s.base_url,
        category=s.category,
        allowed_domains=s.allowed_domains,
        api_access=s.api_access,
        notes=s.notes,
    )


def _opportunity(o: OpportunitySeed, now: datetime) -> Opportunity:
    v = o.verification
    eligibility = o.eligibility.model_dump(mode="json") if o.eligibility else None
    return Opportunity(
        slug=o.slug,
        source_id=o.source,
        kind=o.kind,
        title=o.title,
        summary=o.summary,
        provider=o.provider,
        url=o.url,
        keywords=o.keywords,
        scope=o.scope.model_dump(mode="json"),
        eligibility=eligibility,
        required_documents=o.required_documents,
        application_deadline=o.application_deadline,
        expires_on=o.expires_on,
        benefits=[b.model_dump(mode="json") for b in o.benefits],
        verification_status=Verification(v.status),
        verified_fields=list(v.verified_fields),
        verified_at=v.verified_at,
        verified_by=v.verified_by,
        human_reviewed=v.human_reviewed,
        evidence=[e.model_dump(mode="json") for e in v.evidence],
        publication_status=Publication.PUBLISHED,
        retrieved_at=now,
        search_text=build_search_text(o.title, o.summary, o.provider, o.keywords),
    )


def _career(c: CareerSeed) -> Career:
    return Career(
        slug=c.slug,
        family=c.family,
        title=c.title,
        description=c.description,
        activities=c.activities,
        skills=c.skills,
        entry=c.entry.model_dump(mode="json"),
        routes=[r.model_dump(mode="json") for r in c.routes],
        related=c.related,
        learning_resources=c.learning_resources,
        keywords=c.keywords,
        source_refs=[r.model_dump(mode="json") for r in c.source_refs],
        verification_status="unverified",
        human_reviewed=False,
        localization_status="unreviewed",
        search_text=build_search_text(c.title, c.description, c.activities, c.skills, c.keywords),
    )


def _merge_all(db: Session, rows: Iterable[object]) -> int:
    n = 0
    for row in rows:
        db.merge(row)
        n += 1
    return n


def upsert_bundle(db: Session, bundle: SeedBundle) -> dict[str, int]:
    """All-or-nothing: one transaction. Sources go first so foreign keys resolve."""
    now = datetime.now(UTC)
    try:
        counts = {"sources": _merge_all(db, map(_source, bundle.sources))}
        db.flush()
        counts["opportunities"] = _merge_all(
            db, (_opportunity(o, now) for o in bundle.opportunities)
        )
        counts["careers"] = _merge_all(db, map(_career, bundle.careers))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return counts
