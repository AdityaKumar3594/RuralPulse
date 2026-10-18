from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.localize import Localizer
from app.core.text import tokenize
from app.modules.catalog.models import Career
from app.modules.identity.models import User
from app.modules.profile import service as profile_service
from app.modules.profile.models import Provenance
from app.modules.recommend.engine import (
    CareerDoc,
    ProfileTerm,
    RankingConfig,
    StudentView,
    rank,
)
from app.modules.recommend.models import RecommendationRun
from app.modules.sources.freshness import freshness
from app.modules.sources.models import Opportunity, Source

TERM_FIELDS = ("goals", "interests", "skills", "subject_preferences")
# Question that collects each profile field, so the response can say what to ask next.
QUESTION_FOR_FIELD = {
    "goals": "q_goals",
    "interests": "q_interests",
    "skills": "q_skills",
    "education_stage": "q_education_stage",
}


def _phrases(values: list[str]) -> list[tuple[str, tuple[str, ...]]]:
    out = []
    for text in values:
        tokens = tuple(tokenize(text))
        if tokens:
            out.append((text, tokens))
    return out


def career_doc(career: Career) -> CareerDoc:
    """Flatten a catalog record (all languages) into the token sets the ranker matches against."""

    def langs(value: dict[str, Any]) -> list[str]:
        return [v for v in value.values() if isinstance(v, str)]

    def lang_lists(value: dict[str, list[str]]) -> list[str]:
        return [item for items in value.values() for item in items]

    return CareerDoc(
        slug=career.slug,
        family=career.family,
        fields={
            "keywords": tuple(_phrases(career.keywords)),
            "title": tuple(_phrases(langs(career.title))),
            "skills": tuple(_phrases(lang_lists(career.skills))),
            "activities": tuple(_phrases(lang_lists(career.activities))),
            "description": tuple(_phrases(langs(career.description))),
        },
        min_stage=career.entry.get("typical_min_stage"),
    )


def student_view(db: Session, user: User) -> tuple[StudentView, dict[str, Any]]:
    """The student's own statements as ranking terms. Hypotheses are counted but never used."""
    terms: dict[tuple[str, tuple[str, ...]], ProfileTerm] = {}
    stage: dict[str, str] = {}
    hypotheses = 0
    for e in profile_service.current_entries(db, user.id):
        if e.provenance is Provenance.HYPOTHESIS:
            hypotheses += 1
            continue
        if e.provenance not in (Provenance.REPORTED, Provenance.OBSERVED) or e.value is None:
            continue
        basis = e.provenance.value
        if e.key == "education_stage":
            stage[basis] = e.value
        if e.key in TERM_FIELDS and isinstance(e.value, list):
            for text, tokens in _phrases([v for v in e.value if isinstance(v, str)]):
                key = (e.key, tokens)
                # The same statement both reported and observed counts once, as observed.
                if key not in terms or basis == "observed":
                    terms[key] = ProfileTerm(e.key, text, tokens, basis)  # type: ignore[arg-type]
    ordered = tuple(sorted(terms.values(), key=lambda t: (t.field, t.text)))
    view = StudentView(
        terms=ordered,
        stage=stage.get("reported") or stage.get("observed"),
        seed=str(user.id),
    )
    summary = {
        "terms": [{"field": t.field, "text": t.text, "basis": t.basis} for t in ordered],
        "education_stage": view.stage,
        "hypotheses_ignored": hypotheses,
    }
    return view, summary


def run_for_student(
    db: Session, user: User, config: RankingConfig, limit: int
) -> RecommendationRun:
    view, summary = student_view(db, user)
    docs = [career_doc(c) for c in db.scalars(select(Career))]
    result = rank(view, docs, config, limit)
    data = result.to_dict()
    run = RecommendationRun(
        user_id=user.id,
        ranking_version=data["ranking_version"],
        status=data["status"],
        config=data["config"],
        profile_summary=summary,
        results=data["recommendations"],
    )
    run.profile_summary = {**summary, "unmatched_terms": data["unmatched_terms"]}
    db.add(run)
    # Audit that a run happened and how many came out; the terms stay in the run record.
    audit(
        db,
        "recommendation.run",
        actor_id=user.id,
        subject_user_id=user.id,
        status=run.status,
        count=len(run.results),
    )
    db.commit()
    return run


def latest_run(db: Session, user: User) -> RecommendationRun | None:
    return db.scalar(
        select(RecommendationRun)
        .where(RecommendationRun.user_id == user.id)
        .order_by(RecommendationRun.created_at.desc())
        .limit(1)
    )


def _opportunity_card(
    opp: Opportunity, src: Source | None, loc: Localizer, fresh_days: int, today: date
) -> dict[str, Any]:
    return {
        "slug": opp.slug,
        "title": loc.text(opp.title),
        "url": opp.url,
        "kind": opp.kind,
        "source": loc.text(src.name) if src else None,
        "verification_status": opp.verification_status.value,
        "verified_fields": opp.verified_fields,
        "freshness": freshness(opp, today, fresh_days),
    }


def run_out(
    db: Session, run: RecommendationRun, lang: str, fresh_days: int, today: date | None = None
) -> dict[str, Any]:
    """Language-neutral run plus current catalog details: titles, routes, sources, next steps."""
    today = today or datetime.now(UTC).date()
    slugs = [r["slug"] for r in run.results]
    careers = {c.slug: c for c in db.scalars(select(Career).where(Career.slug.in_(slugs)))}
    opp_slugs = {
        s
        for c in careers.values()
        for s in [r["opportunity"] for r in c.routes if r.get("opportunity")] + c.learning_resources
    }
    opps = {
        o.slug: o for o in db.scalars(select(Opportunity).where(Opportunity.slug.in_(opp_slugs)))
    }
    sources = {s.id: s for s in db.scalars(select(Source))}

    items = []
    for rec in run.results:
        career = careers.get(rec["slug"])
        if career is None:  # removed from the catalog since the run: skip rather than guess
            continue
        loc = Localizer(lang)
        routes = []
        route_sources: dict[str, dict[str, Any]] = {}
        for r in career.routes:
            card = None
            if r.get("opportunity") in opps:
                opp = opps[r["opportunity"]]
                card = _opportunity_card(opp, sources.get(opp.source_id), loc, fresh_days, today)
                route_sources[opp.slug] = card
            routes.append(
                {
                    "kind": r["kind"],
                    "title": loc.text(r["title"]),
                    "min_stage": r.get("min_stage"),
                    "opportunity": card,
                }
            )
        for slug in career.learning_resources:
            if slug in opps and slug not in route_sources:
                opp = opps[slug]
                route_sources[slug] = _opportunity_card(
                    opp, sources.get(opp.source_id), loc, fresh_days, today
                )
        actions: list[dict[str, Any]] = [{"type": "view_career", "career": career.slug}]
        if rec["stage"]["status"] == "below":
            actions.append(
                {
                    "type": "plan_prerequisite",
                    "typical_min_stage": rec["stage"]["typical_min_stage"],
                }
            )
        if rec["stage"]["status"] == "unknown" and rec["stage"]["typical_min_stage"]:
            actions.append(
                {"type": "tell_us", "fact": "education_stage", "question_id": "q_education_stage"}
            )
        actions += [
            {
                "type": "open_route",
                "route_kind": r["kind"],
                "opportunity": r["opportunity"]["slug"],
                "url": r["opportunity"]["url"],
            }
            for r in routes
            if r["opportunity"]
        ]
        items.append(
            {
                **rec,
                "career": {
                    "slug": career.slug,
                    "family": career.family,
                    "title": loc.text(career.title),
                    "description": loc.text(career.description),
                    "entry_notes": loc.text(career.entry.get("notes")),
                },
                "routes": routes,
                "sources": list(route_sources.values()),
                "next_actions": actions,
                "flags": [
                    *(
                        ["catalog_entry_unverified"]
                        if career.verification_status != "verified"
                        else []
                    ),
                    "entry_requirements_are_typical_not_official",
                ],
                "language_fallback": loc.fell_back,
            }
        )
    told = {t["field"] for t in run.profile_summary["terms"]}
    missing = [
        {"field": f, "question_id": q}
        for f, q in QUESTION_FOR_FIELD.items()
        if f != "education_stage" and f not in told
    ]
    if run.profile_summary.get("education_stage") is None:
        missing.append({"field": "education_stage", "question_id": "q_education_stage"})
    return {
        "id": run.id,
        "ranking_version": run.ranking_version,
        "status": run.status,
        "created_at": run.created_at,
        "families": sorted({i["family"] for i in items}),
        "profile_summary": run.profile_summary,
        "missing": missing,
        "items": items,
        "notes": [
            "points_are_keyword_evidence_not_a_probability",
            "interest_is_not_ability",
            "eligibility_is_checked_separately",
        ],
    }
