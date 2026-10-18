import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.base import LLMProvider
from app.core.audit import audit
from app.core.config import Settings
from app.modules.eligibility import service as eligibility_service
from app.modules.explain import evidence as ev
from app.modules.explain.llm import PROMPT_VERSION, generate
from app.modules.explain.models import Explanation
from app.modules.explain.validate import validate_explanation
from app.modules.identity.models import User
from app.modules.pathway import service as pathway_service
from app.modules.recommend import service as recommend_service
from app.modules.sources import service as sources_service
from app.modules.sources.models import Source


class ExplainError(Exception):
    pass


class RefNotFound(ExplainError):
    pass


class BadRef(ExplainError):
    pass


def _build(
    db: Session, user: User, kind: str, ref: dict[str, Any], lang: str, fresh_days: int
) -> tuple[dict, set[str], str | None, Any]:
    """Resolve what is being explained into (evidence, allowed urls, outcome, template fn)."""
    if kind == "recommendation":
        if not (ref.get("run_id") and ref.get("career")):
            raise BadRef
        run = db.get(recommend_service.RecommendationRun, ref["run_id"])
        if run is None or run.user_id != user.id:
            raise RefNotFound
        out = recommend_service.run_out(db, run, lang, fresh_days)
        item = next((i for i in out["items"] if i["slug"] == ref["career"]), None)
        if item is None:
            raise RefNotFound
        evidence, urls, outcome = ev.recommendation_evidence(item, lang)
        return evidence, urls, outcome, ev.recommendation_template
    if kind == "eligibility":
        if not ref.get("evaluation_id"):
            raise BadRef
        row = db.get(eligibility_service.EligibilityEvaluation, ref["evaluation_id"])
        if row is None or row.user_id != user.id:
            raise RefNotFound
        opp = db.get(eligibility_service.Opportunity, row.opportunity_slug)
        src = db.get(Source, opp.source_id)
        opp_out = sources_service.opportunity_out(opp, src, lang, fresh_days)
        evaluation = eligibility_service.evaluation_out(db, row, lang)
        evidence, urls, outcome = ev.eligibility_evidence(evaluation, opp_out, lang)
        return evidence, urls, outcome, ev.eligibility_template
    if kind == "pathway":
        if not ref.get("plan_id"):
            raise BadRef
        plan = pathway_service.get_plan_or_none(db, user, ref["plan_id"])
        if plan is None:
            raise RefNotFound
        evidence, urls, outcome = ev.pathway_evidence(
            pathway_service.plan_out(db, plan, lang, fresh_days), lang
        )
        return evidence, urls, outcome, ev.pathway_template
    raise BadRef


def explain(
    db: Session,
    llm: LLMProvider | None,
    settings: Settings,
    user: User,
    kind: str,
    ref: dict[str, Any],
    lang: str,
) -> dict[str, Any]:
    evidence, urls, outcome, template = _build(
        db, user, kind, ref, lang, settings.source_fresh_days
    )
    digest = hashlib.sha256(
        (
            json.dumps(evidence, sort_keys=True, ensure_ascii=False, default=str)
            + lang
            + PROMPT_VERSION
        ).encode()
    ).hexdigest()

    # Same evidence, same words: reuse an earlier AI explanation instead of paying again.
    cached = db.scalar(
        select(Explanation)
        .where(
            Explanation.user_id == user.id,
            Explanation.evidence_hash == digest,
            Explanation.source == "ai",
        )
        .order_by(Explanation.created_at.desc())
        .limit(1)
    )
    if cached is not None:
        return _out(cached, urls_for(evidence), cached=True)

    output: dict[str, Any] | None = None
    source, reason, model = "template", None, None
    if llm is None:
        reason = "ai_not_configured"
    else:
        since = datetime.now(UTC) - timedelta(days=1)
        used = db.scalar(
            select(func.count())
            .select_from(Explanation)
            .where(
                Explanation.user_id == user.id,
                Explanation.source == "ai",
                Explanation.created_at >= since,
            )
        )
        if used >= settings.ai_daily_limit:
            reason = "daily_limit"
        else:
            candidate, failure = generate(llm, evidence)
            if failure:
                reason = failure
            else:
                violations = validate_explanation(
                    candidate, evidence, language=lang, outcome=outcome, allowed_urls=urls
                )
                if violations:
                    reason = "validation_failed:" + ",".join(violations)
                else:
                    output, source, model = candidate, "ai", llm.model
    if output is None:
        output = template(evidence)
    row = Explanation(
        user_id=user.id,
        kind=kind,
        language=lang,
        source=source,
        fallback_reason=reason,
        model=model,
        evidence_hash=digest,
        output=output,
    )
    db.add(row)
    # Audit that an explanation was produced, never its content.
    audit(
        db,
        "explanation.created",
        actor_id=user.id,
        subject_user_id=user.id,
        kind=kind,
        source=source,
    )
    db.commit()
    return _out(row, urls_for(evidence))


def urls_for(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Sources the explanation may cite, shown next to it."""
    found: list[dict[str, Any]] = []
    if evidence["kind"] == "eligibility":
        o = evidence["opportunity"]
        found.append(
            {"title": o["title"], "url": o["url"], "freshness": evidence["record"]["freshness"]}
        )
    for s in evidence.get("sources", []):
        found.append({"title": s["title"], "url": s["url"], "freshness": s["freshness"]})
    return found


def _out(row: Explanation, sources: list[dict[str, Any]], cached: bool = False) -> dict[str, Any]:
    return {
        "id": row.id,
        "kind": row.kind,
        "language": row.language,
        "source": row.source,
        "fallback_reason": None
        if row.source == "ai"
        else (row.fallback_reason or "").split(":")[0],
        "model": row.model,
        "cached": cached,
        "explanation": row.output,
        "sources": sources,
        "created_at": row.created_at,
    }


def _uuid(value: Any) -> uuid.UUID | None:  # pragma: no cover - helper for routers
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None
