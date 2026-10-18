import uuid
from pathlib import Path

import pytest

from app.ingestion.bundle import load_bundle
from app.ingestion.loader import _career
from app.modules.pathway.planner import (
    CareerInput,
    Plan,
    RouteInput,
    build_plan,
    check_consistency,
)
from app.modules.pathway.service import career_input
from tests.conftest import auth_headers, register

REAL_SEED = Path(__file__).resolve().parents[2] / "data" / "seed"

NURSE = CareerInput(
    "nurse",
    routes=(RouteInput("diploma", "class_12"), RouteInput("degree", "class_12")),
    skill_count=3,
)


def ids(plan):
    return [s["id"] for s in plan.steps]


def step(plan, sid):
    return next(s for s in plan.steps if s["id"] == sid)


# --- planner ---


def test_stage_step_is_added_once_and_both_routes_depend_on_it():
    plan = build_plan(NURSE, "class_10")
    assert ids(plan).count("stage:class_12") == 1
    assert step(plan, "route:0")["depends_on"] == ["stage:class_12"]
    assert step(plan, "route:1")["depends_on"] == ["stage:class_12"]
    assert ids(plan).index("stage:class_12") < ids(plan).index("route:0")


def test_no_stage_step_when_the_student_already_meets_it():
    plan = build_plan(NURSE, "undergraduate")
    assert not any(s["type"] == "qualification" for s in plan.steps)
    assert step(plan, "route:0")["depends_on"] == []


def test_unknown_stage_adds_a_check_in_step_first_and_routes_wait_for_it():
    plan = build_plan(NURSE, None)
    assert ids(plan)[0] == "tell_us_stage"
    assert step(plan, "route:0")["depends_on"] == ["tell_us_stage"]
    assert step(plan, "tell_us_stage")["completion_criteria"]["field"] == "education_stage"


def test_routes_are_alternatives_not_a_sequence():
    plan = build_plan(NURSE, "class_10")
    assert plan.alternatives == ["route:0", "route:1"]
    assert "route:0" not in step(plan, "route:1")["depends_on"]


def test_higher_stages_chain_in_order():
    career = CareerInput(
        "x", routes=(RouteInput("degree", "undergraduate"), RouteInput("diploma", "class_12"))
    )
    plan = build_plan(career, "class_10")
    assert step(plan, "stage:undergraduate")["depends_on"] == ["stage:class_12"]
    assert ids(plan).index("stage:class_12") < ids(plan).index("stage:undergraduate")


def test_preparation_is_suggested_never_required_and_effort_is_never_invented():
    career = CareerInput(
        "x",
        routes=(RouteInput("on_the_job", None),),
        skill_count=2,
        learning_resources=("diksha-portal",),
    )
    plan = build_plan(career, "class_10")
    levels = {s["id"]: s["requirement_level"] for s in plan.steps}
    assert (
        levels["skills"] == "suggested_preparation"
        and levels["resource:diksha-portal"] == "suggested_preparation"
    )
    assert levels["route:0"] == "typical_route"
    assert "official_requirement" not in set(levels.values())  # no verified source exists yet
    assert all(s["estimated_effort"] is None for s in plan.steps)
    assert {
        "effort_not_available",
        "cost_not_available",
        "requirements_are_typical_not_official",
    } <= set(plan.unknowns)


def test_exam_routes_become_exam_preparation_without_naming_an_exam():
    career = CareerInput("x", routes=(RouteInput("competitive_exam", None),))
    assert build_plan(career, "class_12").steps[0]["type"] == "exam_preparation"


def test_consistency_checker_rejects_broken_plans():
    good = build_plan(NURSE, "class_10")
    check_consistency(good)
    dup = Plan(steps=[*good.steps, dict(good.steps[0])], alternatives=[])
    with pytest.raises(ValueError, match="duplicate"):
        check_consistency(dup)
    missing = Plan(steps=[{**good.steps[0], "depends_on": ["ghost"]}], alternatives=[])
    with pytest.raises(ValueError, match="does not come before"):
        check_consistency(missing)
    out_of_order = Plan(steps=list(reversed(good.steps)), alternatives=[])
    with pytest.raises(ValueError):
        check_consistency(out_of_order)
    with pytest.raises(ValueError, match="not a step"):
        check_consistency(Plan(steps=good.steps, alternatives=["route:99"]))


def test_every_real_career_yields_a_consistent_plan_for_every_stage():
    careers = [career_input(_career(c)) for c in load_bundle(REAL_SEED).careers]
    for career in careers:
        for stage in (None, "class_9", "class_10", "class_12", "undergraduate", "not_in_school"):
            plan = build_plan(career, stage)
            check_consistency(plan)
            assert plan.alternatives and len(plan.alternatives) == len(career.routes)


# --- API ---


@pytest.fixture
def student(seeded):
    headers = auth_headers(register(seeded))
    seeded.post("/api/consents", json={"given_by": "self"}, headers=headers)
    return headers


def create(client, headers, career="electrician", **extra):
    return client.post("/api/pathways", json={"career": career, **extra}, headers=headers)


def step_status(client, headers, plan_id, step_id, status):
    return client.put(
        f"/api/pathways/{plan_id}/steps/{step_id}", json={"status": status}, headers=headers
    )


def test_requires_login_and_consent(seeded):
    assert seeded.post("/api/pathways", json={"career": "electrician"}).status_code == 401
    h = auth_headers(register(seeded))
    assert (
        seeded.post("/api/pathways", json={"career": "electrician"}, headers=h).status_code == 403
    )


def test_plan_is_built_from_the_catalog_with_resources_and_honest_labels(student, seeded):
    seeded.put("/api/profile/fields/education_stage", json={"value": "class_9"}, headers=student)
    r = create(seeded, student)
    assert r.status_code == 201
    plan = r.json()
    assert plan["career"]["slug"] == "electrician" and plan["student_stage"] == "class_9"
    by_id = {s["id"]: s for s in plan["steps"]}
    assert by_id["stage:class_10"]["title"].startswith("Complete Class 10")
    assert by_id["stage:class_10"]["requirement_level"] == "typical_route"
    assert by_id["route:0"]["depends_on"] == ["stage:class_10"]
    assert by_id["route:1"]["resource"]["slug"] == "national-learning-platform"
    assert by_id["route:1"]["resource"]["freshness"] == "fresh"
    assert (
        by_id["resource:national-learning-platform"]["requirement_level"] == "suggested_preparation"
    )
    assert all(s["estimated_effort"] is None for s in plan["steps"])
    assert "requirements_are_typical_not_official" in plan["unknowns"]


def test_tamil_titles_and_unknown_career(student, seeded):
    seeded.put("/api/profile/fields/education_stage", json={"value": "class_9"}, headers=student)
    plan = create(seeded, student, language="ta").json()
    stage = next(s for s in plan["steps"] if s["id"] == "stage:class_10")
    assert "10ஆம் வகுப்பு" in stage["title"]
    assert create(seeded, student, career="ghost").status_code == 404


def test_existing_plan_is_returned_with_its_progress_unless_refreshed(student, seeded):
    first = create(seeded, student).json()
    again = create(seeded, student)
    assert again.status_code == 200 and again.json()["id"] == first["id"]
    refreshed = create(seeded, student, refresh=True)
    assert refreshed.status_code == 201 and refreshed.json()["id"] != first["id"]
    assert len(seeded.get("/api/pathways", headers=student).json()) == 2


def test_progress_respects_prerequisites_in_both_directions(student, seeded):
    seeded.put("/api/profile/fields/education_stage", json={"value": "class_9"}, headers=student)
    plan = create(seeded, student).json()
    pid = plan["id"]
    # Cannot start the ITI route before finishing Class 10.
    r = step_status(seeded, student, pid, "route:0", "in_progress")
    assert (r.status_code, r.json()["detail"]) == (409, "prerequisites_not_done")
    assert step_status(seeded, student, pid, "stage:class_10", "done").status_code == 200
    assert step_status(seeded, student, pid, "route:0", "in_progress").status_code == 200
    # Cannot un-finish Class 10 while the route that depends on it has started.
    r = step_status(seeded, student, pid, "stage:class_10", "not_started")
    assert (r.status_code, r.json()["detail"]) == (409, "dependent_steps_started")
    assert step_status(seeded, student, pid, "route:0", "not_started").status_code == 200
    assert step_status(seeded, student, pid, "stage:class_10", "not_started").status_code == 200
    got = seeded.get(f"/api/pathways/{pid}", headers=student).json()
    assert {s["id"]: s["status"] for s in got["steps"]}["stage:class_10"] == "not_started"


def test_independent_steps_have_no_prerequisites_and_notes_are_kept(student, seeded):
    plan = create(seeded, student).json()
    r = seeded.put(
        f"/api/pathways/{plan['id']}/steps/skills",
        json={"status": "done", "note": "Practised wiring at home"},
        headers=student,
    )
    assert r.status_code == 200
    step = next(s for s in r.json()["steps"] if s["id"] == "skills")
    assert step["status"] == "done" and step["note"] == "Practised wiring at home"


def test_validation_and_unknown_step_and_privacy(student, seeded):
    plan = create(seeded, student).json()
    assert step_status(seeded, student, plan["id"], "nope", "done").status_code == 404
    assert step_status(seeded, student, plan["id"], "skills", "finished").status_code == 422
    other = auth_headers(register(seeded, phone="9000000005"))
    seeded.post("/api/consents", json={"given_by": "self"}, headers=other)
    assert seeded.get(f"/api/pathways/{plan['id']}", headers=other).status_code == 404
    assert step_status(seeded, other, plan["id"], "skills", "done").status_code == 404
    assert seeded.get(f"/api/pathways/{uuid.uuid4()}", headers=student).status_code == 404
    assert seeded.get("/api/pathways", headers=other).json() == []
