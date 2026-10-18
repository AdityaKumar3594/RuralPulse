from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.localize import Localizer
from app.modules.sources.freshness import freshness
from app.modules.sources.models import Opportunity, Publication, Source


def list_sources(db: Session) -> list[Source]:
    return list(db.scalars(select(Source).order_by(Source.id)))


def get_opportunity(db: Session, slug: str) -> Opportunity | None:
    opp = db.get(Opportunity, slug)
    return opp if opp and opp.publication_status is Publication.PUBLISHED else None


def source_brief(src: Source, loc: Localizer) -> dict[str, Any]:
    return {
        "id": src.id,
        "name": loc.text(src.name),
        "publisher": src.publisher,
        "base_url": src.base_url,
    }


def flags_for(opp: Opportunity, fresh: str) -> list[str]:
    """Plain-language caveats that downstream explanations must not drop."""
    flags = []
    if fresh == "expired":
        flags.append("expired_or_deadline_passed")
    if fresh == "stale":
        flags.append("needs_reverification")
    if fresh == "unverified":
        flags.append("unverified")
    if opp.verification_status.value == "verified" and not opp.human_reviewed:
        flags.append("not_human_reviewed")
    if "eligibility" not in opp.verified_fields:
        flags.append("eligibility_not_verified")
    if opp.application_deadline is None:
        flags.append("deadline_unknown")
    return flags


def opportunity_out(
    opp: Opportunity, src: Source, lang: str, fresh_days: int, today: date | None = None
) -> dict[str, Any]:
    loc = Localizer(lang)
    today = today or datetime.now(UTC).date()
    fresh = freshness(opp, today, fresh_days)
    eligibility = dict(opp.eligibility) if opp.eligibility else None
    if eligibility is not None:
        eligibility["text"] = loc.text(eligibility.get("text"))
        eligibility["other_criteria"] = [
            loc.text(c) for c in eligibility.get("other_criteria") or []
        ]
    return {
        "slug": opp.slug,
        "kind": opp.kind,
        "title": loc.text(opp.title),
        "summary": loc.text(opp.summary),
        "provider": opp.provider,
        "url": opp.url,
        "source": source_brief(src, loc),
        "scope": opp.scope,
        "eligibility": eligibility,
        "required_documents": opp.required_documents,
        "application_deadline": opp.application_deadline,
        "expires_on": opp.expires_on,
        "benefits": [
            {
                "text": loc.text(b["text"]),
                "amount_inr": b.get("amount_inr"),
                "period": b.get("period"),
            }
            for b in opp.benefits
        ],
        "verification": {
            "status": opp.verification_status.value,
            "verified_fields": opp.verified_fields,
            "verified_at": opp.verified_at,
            "verified_by": opp.verified_by,
            "human_reviewed": opp.human_reviewed,
            "evidence": opp.evidence,
        },
        "freshness": fresh,
        "flags": flags_for(opp, fresh),
        "language": lang,
        "language_fallback": loc.fell_back,
    }
