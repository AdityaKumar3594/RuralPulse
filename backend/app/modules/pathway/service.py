import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.localize import Localizer
from app.modules.catalog.models import Career
from app.modules.identity.models import User
from app.modules.pathway import texts
from app.modules.pathway.models import PathwayPlan, PathwayStepProgress
from app.modules.pathway.planner import CareerInput, RouteInput, build_plan
from app.modules.profile import service as profile_service
from app.modules.profile.models import Provenance
from app.modules.sources.freshness import freshness
from app.modules.sources.models import Opportunity, Source

STATUSES = ("not_started", "in_progress", "done")
# Opportunity kinds that publish eligibility criteria worth checking.
CHECKABLE_KINDS = {"scheme", "scholarship", "apprenticeship", "internship", "job"}


class PathwayError(Exception):
    pass


class CareerNotFound(PathwayError):
    pass


class PlanNotFound(PathwayError):
    pass


class UnknownStep(PathwayError):
    pass


class PrerequisitesNotDone(PathwayError):
    pass


class DependentStepsStarted(PathwayError):
    pass


def _student_stage(db: Session, user_id: uuid.UUID) -> str | None:
    found: dict[str, str] = {}
    for e in profile_service.current_entries(db, user_id):
        if e.key == "education_stage" and e.provenance in (
            Provenance.REPORTED,
            Provenance.OBSERVED,
        ):
            found.setdefault(e.provenance.value, e.value)
    return found.get("reported") or found.get("observed")


def career_input(career: Career) -> CareerInput:
    return CareerInput(
        slug=career.slug,
        routes=tuple(
            RouteInput(r["kind"], r.get("min_stage"), r.get("opportunity")) for r in career.routes
        ),
        skill_count=len(career.skills.get("en", [])),
        learning_resources=tuple(career.learning_resources),
    )


def create_plan(
    db: Session, user: User, career_slug: str, refresh: bool
) -> tuple[PathwayPlan, bool]:
    """Return (plan, created). An existing plan is kept (with its progress) unless refresh."""
    career = db.get(Career, career_slug)
    if career is None:
        raise CareerNotFound
    existing = db.scalar(
        select(PathwayPlan)
        .where(PathwayPlan.user_id == user.id, PathwayPlan.career_slug == career_slug)
        .order_by(PathwayPlan.created_at.desc())
        .limit(1)
    )
    if existing is not None and not refresh:
        return existing, False
    stage = _student_stage(db, user.id)
    plan = build_plan(career_input(career), stage)
    row = PathwayPlan(
        user_id=user.id,
        career_slug=career_slug,
        version=plan.version,
        student_stage=stage,
        steps=plan.steps,
        alternatives=plan.alternatives,
        unknowns=plan.unknowns,
    )
    db.add(row)
    audit(db, "pathway.created", actor_id=user.id, subject_user_id=user.id, career=career_slug)
    db.commit()
    return row, True


def get_plan(db: Session, user: User, plan_id: uuid.UUID) -> PathwayPlan:
    plan = db.get(PathwayPlan, plan_id)
    if plan is None or plan.user_id != user.id:
        raise PlanNotFound
    return plan


def get_plan_or_none(db: Session, user: User, plan_id: uuid.UUID) -> PathwayPlan | None:
    plan = db.get(PathwayPlan, plan_id)
    return plan if plan is not None and plan.user_id == user.id else None


def list_plans(db: Session, user: User) -> list[PathwayPlan]:
    return list(
        db.scalars(
            select(PathwayPlan)
            .where(PathwayPlan.user_id == user.id)
            .order_by(PathwayPlan.created_at.desc())
        )
    )


def progress_map(db: Session, plan_id: uuid.UUID) -> dict[str, PathwayStepProgress]:
    rows = db.scalars(select(PathwayStepProgress).where(PathwayStepProgress.plan_id == plan_id))
    return {r.step_id: r for r in rows}


def set_progress(
    db: Session,
    plan: PathwayPlan,
    step_id: str,
    status: str,
    note: str | None,
    actor_id: uuid.UUID,
) -> PathwayStepProgress:
    """Move a step's status while keeping the plan consistent.

    A step can start only when everything it depends on is done, and a step can go back to
    "not started" only if no step that depends on it has started.
    """
    steps = {s["id"]: s for s in plan.steps}
    if step_id not in steps:
        raise UnknownStep
    progress = progress_map(db, plan.id)

    def current(sid: str) -> str:
        return progress[sid].status if sid in progress else "not_started"

    if status != "not_started":
        if any(current(dep) != "done" for dep in steps[step_id]["depends_on"]):
            raise PrerequisitesNotDone
    else:
        dependents = [s["id"] for s in plan.steps if step_id in s["depends_on"]]
        if any(current(d) != "not_started" for d in dependents):
            raise DependentStepsStarted
    row = progress.get(step_id)
    if row is None:
        row = PathwayStepProgress(plan_id=plan.id, step_id=step_id, status=status)
        db.add(row)
    row.status, row.note, row.updated_by = status, note, actor_id
    row.updated_at = datetime.now(UTC)
    audit(
        db,
        "pathway.progress",
        actor_id=actor_id,
        subject_user_id=plan.user_id,
        step=step_id,
        status=status,
    )
    db.commit()
    return row


def plan_out(db: Session, plan: PathwayPlan, lang: str, fresh_days: int) -> dict[str, Any]:
    career = db.get(Career, plan.career_slug)
    loc = Localizer(lang)
    opp_slugs = {s["opportunity"] for s in plan.steps if s.get("opportunity")}
    opps = {
        o.slug: o for o in db.scalars(select(Opportunity).where(Opportunity.slug.in_(opp_slugs)))
    }
    sources = {s.id: s for s in db.scalars(select(Source))}
    progress = progress_map(db, plan.id)
    today = datetime.now(UTC).date()

    steps = []
    for s in plan.steps:
        opp = opps.get(s.get("opportunity") or "")
        card = None
        if opp is not None:
            card = {
                "slug": opp.slug,
                "title": loc.text(opp.title),
                "url": opp.url,
                "kind": opp.kind,
                "source": loc.text(sources[opp.source_id].name),
                "verification_status": opp.verification_status.value,
                "freshness": freshness(opp, today, fresh_days),
                "check_eligibility": opp.kind in CHECKABLE_KINDS and bool(opp.eligibility),
            }
        route = career.routes[s["route_index"]] if s.get("route_index") is not None else None
        if s["type"] == "check_in":
            title = texts.step_title("tell_us_stage", lang)
        elif s["type"] == "qualification":
            title = texts.step_title(
                "complete_stage", lang, stage=texts.stage_label(s["stage"], lang)
            )
        elif s["type"] == "skill_building":
            title = texts.step_title("skills", lang)
        elif route is not None:
            title = loc.text(route["title"])
        else:
            title = loc.text(opp.title) if opp else s["id"]
        done = progress.get(s["id"])
        steps.append(
            {
                **s,
                "title": title,
                "skills": loc.items(career.skills) if s["type"] == "skill_building" else None,
                "resource": card,
                "status": done.status if done else "not_started",
                "note": done.note if done else None,
            }
        )
    return {
        "id": plan.id,
        "career": {"slug": career.slug, "title": loc.text(career.title), "family": career.family},
        "version": plan.version,
        "student_stage": plan.student_stage,
        "created_at": plan.created_at,
        "steps": steps,
        "alternatives": plan.alternatives,
        "unknowns": plan.unknowns,
        "language_fallback": loc.fell_back,
    }
