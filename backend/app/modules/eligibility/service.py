import hashlib
import json
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.localize import Localizer
from app.modules.eligibility.engine import (
    Evaluation,
    FactValue,
    OpportunityRules,
    StudentFacts,
    evaluate,
    resolve,
)
from app.modules.eligibility.models import EligibilityEvaluation
from app.modules.identity.models import User
from app.modules.profile import service as profile_service
from app.modules.profile.models import Provenance
from app.modules.sources.models import Opportunity

# Which interview question collects each fact (None: asked at registration).
QUESTION_FOR_FACT = {
    "education_stage": "q_education_stage",
    "state": "q_state",
    "annual_family_income_inr": "q_annual_family_income",
    "date_of_birth": None,
}


def build_facts(db: Session, user: User) -> StudentFacts:
    """Student facts from the profile. Hypotheses and 'unknown' entries never count as facts."""
    by_key: dict[str, list[FactValue]] = {}
    for e in profile_service.current_entries(db, user.id):
        if e.provenance in (Provenance.REPORTED, Provenance.OBSERVED) and e.value is not None:
            by_key.setdefault(e.key, []).append(FactValue(e.value, e.provenance.value))
    return StudentFacts(
        birth_date=user.date_of_birth,
        education_stage=resolve(by_key.get("education_stage", [])),
        state=resolve(by_key.get("state", [])),
        annual_family_income_inr=resolve(by_key.get("annual_family_income_inr", [])),
    )


def rules_from_opportunity(opp: Opportunity) -> OpportunityRules:
    return OpportunityRules(
        slug=opp.slug,
        eligibility=opp.eligibility,
        scope_level=opp.scope.get("level", "national"),
        scope_states=opp.scope.get("states", []),
        application_deadline=opp.application_deadline,
        expires_on=opp.expires_on,
        verified_fields=frozenset(opp.verified_fields),
        verified_at=opp.verified_at,
    )


def fingerprint(rules: OpportunityRules) -> str:
    payload = {
        "eligibility": rules.eligibility,
        "scope": [rules.scope_level, sorted(rules.scope_states)],
        "deadline": rules.application_deadline.isoformat() if rules.application_deadline else None,
        "expires_on": rules.expires_on.isoformat() if rules.expires_on else None,
        "verified_fields": sorted(rules.verified_fields),
        "verified_at": rules.verified_at.isoformat() if rules.verified_at else None,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def evaluate_for_student(
    db: Session, user: User, opp: Opportunity, fresh_days: int, today: date | None = None
) -> EligibilityEvaluation:
    today = today or datetime.now(UTC).date()
    rules = rules_from_opportunity(opp)
    result: Evaluation = evaluate(rules, build_facts(db, user), today, fresh_days)
    data = result.to_dict()
    row = EligibilityEvaluation(
        user_id=user.id,
        opportunity_slug=opp.slug,
        outcome=data["outcome"],
        reasons=data["reasons"],
        checks=data["checks"],
        missing=data["missing"],
        flags=data["flags"],
        facts_used=data["facts_used"],
        rules_version=data["rules_version"],
        opportunity_fingerprint=fingerprint(rules),
        record_snapshot={
            "verification_status": opp.verification_status.value,
            "verified_fields": opp.verified_fields,
            "verified_at": opp.verified_at.isoformat() if opp.verified_at else None,
            "human_reviewed": opp.human_reviewed,
            "evidence_urls": [e["url"] for e in opp.evidence],
        },
        evaluated_on=today,
    )
    db.add(row)
    # Audit the outcome, never the facts behind it (they include income and age).
    audit(
        db,
        "eligibility.evaluated",
        actor_id=user.id,
        subject_user_id=user.id,
        opportunity=opp.slug,
        outcome=row.outcome,
    )
    db.commit()
    return row


def history(
    db: Session, user: User, opportunity_slug: str | None, limit: int
) -> list[EligibilityEvaluation]:
    stmt = select(EligibilityEvaluation).where(EligibilityEvaluation.user_id == user.id)
    if opportunity_slug:
        stmt = stmt.where(EligibilityEvaluation.opportunity_slug == opportunity_slug)
    stmt = stmt.order_by(EligibilityEvaluation.evaluated_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def missing_with_questions(missing: list[str]) -> list[dict[str, Any]]:
    return [{"fact": m, "question_id": QUESTION_FOR_FACT.get(m)} for m in missing]


def evaluation_out(db: Session, row: EligibilityEvaluation, lang: str) -> dict[str, Any]:
    opp = db.get(Opportunity, row.opportunity_slug)
    loc = Localizer(lang)
    return {
        "id": row.id,
        "opportunity": {
            "slug": opp.slug,
            "kind": opp.kind,
            "title": loc.text(opp.title),
            "url": opp.url,
        },
        "outcome": row.outcome,
        "reasons": row.reasons,
        "checks": row.checks,
        "missing": missing_with_questions(row.missing),
        "flags": row.flags,
        "facts_used": row.facts_used,
        "rules_version": row.rules_version,
        "opportunity_fingerprint": row.opportunity_fingerprint,
        "record": row.record_snapshot,
        "evaluated_on": row.evaluated_on,
        "evaluated_at": row.evaluated_at,
    }
