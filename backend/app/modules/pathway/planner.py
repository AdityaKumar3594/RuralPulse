"""Pathway planner: ordered, dependency-consistent steps built ONLY from catalog data.

No courses, qualifications, durations or outcomes are invented. What we know per career is its
typical entry stage, its routes (with an optional minimum stage and linked opportunity), its
skills and its learning resources. The plan reshapes that into steps and says plainly what is
unknown. Pure code: no database, no LLM.

Requirement levels (we hold no verified, official prerequisites, so nothing is "mandatory"):
  typical_route          a common way in, from the catalog; not an official rule
  suggested_preparation  helpful, never required
(`official_requirement` is reserved for a future verified source and is never produced now.)
"""

from dataclasses import dataclass, field
from typing import Any

from app.modules.recommend.engine import STAGE_RANK

PATHWAY_VERSION = "2026-10-1"

UNKNOWNS = [
    "effort_not_available",
    "cost_not_available",
    "local_availability_unknown",
    "requirements_are_typical_not_official",
]


@dataclass(frozen=True)
class RouteInput:
    kind: str
    min_stage: str | None = None
    opportunity: str | None = None


@dataclass(frozen=True)
class CareerInput:
    slug: str
    routes: tuple[RouteInput, ...]
    skill_count: int = 0
    learning_resources: tuple[str, ...] = ()


@dataclass
class Plan:
    steps: list[dict[str, Any]] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)  # ids of steps that are either/or
    unknowns: list[str] = field(default_factory=lambda: list(UNKNOWNS))
    version: str = PATHWAY_VERSION


def _step(
    sid: str, type_: str, group: str, depends_on: list[str], level: str, **extra: Any
) -> dict:
    return {
        "id": sid,
        "type": type_,
        "group": group,
        "depends_on": depends_on,
        "requirement_level": level,
        "estimated_effort": None,  # we hold no effort data; never guessed
        "route_index": None,
        "stage": None,
        "opportunity": None,
        "completion_criteria": {"type": "self_report"},
        **extra,
    }


def build_plan(career: CareerInput, student_stage: str | None) -> Plan:
    plan = Plan()
    have = STAGE_RANK.get(student_stage or "")
    stage_steps: dict[str, str] = {}  # stage -> step id
    check_in_id: str | None = None

    def stage_dependency(min_stage: str | None) -> list[str]:
        nonlocal check_in_id
        if min_stage is None or min_stage not in STAGE_RANK:
            return []
        if student_stage is None or have is None:
            # We do not know where the student is: first ask, then plan around the answer.
            if check_in_id is None:
                check_in_id = "tell_us_stage"
                plan.steps.insert(
                    0,
                    _step(
                        check_in_id,
                        "check_in",
                        "foundation",
                        [],
                        "suggested_preparation",
                        completion_criteria={"type": "profile_field", "field": "education_stage"},
                    ),
                )
            return [check_in_id]
        if have >= STAGE_RANK[min_stage]:
            return []  # already there
        return [stage_steps[min_stage]]

    # Stage steps first, lowest to highest, each depending on the next lower one, whatever order
    # the routes are listed in.
    if have is not None:
        needed = sorted(
            {
                r.min_stage
                for r in career.routes
                if r.min_stage in STAGE_RANK and have < STAGE_RANK[r.min_stage]
            },
            key=lambda stage: STAGE_RANK[stage],
        )
        previous: str | None = None
        for stage in needed:
            sid = f"stage:{stage}"
            stage_steps[stage] = sid
            plan.steps.append(
                _step(
                    sid,
                    "qualification",
                    "foundation",
                    [previous] if previous else [],
                    "typical_route",
                    stage=stage,
                    completion_criteria={
                        "type": "profile_field",
                        "field": "education_stage",
                        "reaches": stage,
                    },
                )
            )
            previous = sid

    # Suggested preparation: independent of any route.
    if career.skill_count:
        plan.steps.append(
            _step("skills", "skill_building", "preparation", [], "suggested_preparation")
        )
    for slug in career.learning_resources:
        plan.steps.append(
            _step(
                f"resource:{slug}",
                "learning_resource",
                "preparation",
                [],
                "suggested_preparation",
                opportunity=slug,
            )
        )

    # Routes are alternatives (any one is enough), each behind its own stage prerequisite.
    for i, route in enumerate(career.routes):
        sid = f"route:{i}"
        type_ = "exam_preparation" if route.kind == "competitive_exam" else "route"
        plan.steps.append(
            _step(
                sid,
                type_,
                f"alternative:{i}",
                stage_dependency(route.min_stage),
                "typical_route",
                route_index=i,
                opportunity=route.opportunity,
                route_kind=route.kind,
            )
        )
        plan.alternatives.append(sid)

    # Foundation steps must precede everything that depends on them.
    plan.steps = _topological(plan.steps)
    check_consistency(plan)
    return plan


def _topological(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable order in which every step comes after its dependencies."""
    placed: list[dict[str, Any]] = []
    done: set[str] = set()
    pending = list(steps)
    while pending:
        progressed = False
        for step in list(pending):
            if all(d in done for d in step["depends_on"]):
                placed.append(step)
                done.add(step["id"])
                pending.remove(step)
                progressed = True
        if not progressed:
            raise ValueError("pathway has a dependency cycle")
    return placed


def check_consistency(plan: Plan) -> None:
    """Raise ValueError if ids repeat, a dependency is missing, or order breaks a dependency."""
    seen: set[str] = set()
    for step in plan.steps:
        if step["id"] in seen:
            raise ValueError(f"duplicate step id {step['id']}")
        for dep in step["depends_on"]:
            if dep not in seen:
                raise ValueError(
                    f"step {step['id']} depends on {dep}, which does not come before it"
                )
        seen.add(step["id"])
    for alt in plan.alternatives:
        if alt not in seen:
            raise ValueError(f"alternative {alt} is not a step")
