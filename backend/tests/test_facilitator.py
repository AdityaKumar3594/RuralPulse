import uuid

import pytest
from sqlalchemy import select

from app.core.audit import AuditEvent
from app.modules.profile.models import ProfileEntry
from tests.conftest import (
    MINOR_DOB,
    assign,
    make_student,
    share_with_facilitators,
    staff_headers,
    user_id,
)


@pytest.fixture
def world(seeded, db, admin, facilitator):
    """An assigned student who has NOT yet shared their profile."""
    student = make_student(seeded)
    assign(seeded, admin, facilitator, student)
    return {"student": student, "sid": user_id(seeded, student)}


def url(sid, suffix=""):
    return f"/api/facilitator/students/{sid}{suffix}"


STUDENT_ENDPOINTS = [
    ("get", "/profile", None),
    ("post", "/observations", {"key": "skills", "value": ["wiring"], "basis": "Saw it"}),
    ("post", "/assisted-answers", {"key": "interests", "value": ["farming"]}),
    ("get", "/recommendations/latest", None),
    ("post", "/endorsements", {"opportunity": "fresh-scholarship"}),
    ("get", "/pathways", None),
    ("get", "/applications", None),
]


def call(client, method, path, headers, body=None):
    return getattr(client, method)(
        path, headers=headers, **({"json": body} if body is not None else {})
    )


def test_the_dashboard_lists_only_my_students_and_flags_sharing(
    seeded, db, admin, facilitator, world
):
    other = staff_headers(seeded, db, "facilitator", "9100000050")
    mine = seeded.get("/api/facilitator/students", headers=facilitator).json()
    assert [(s["id"], s["shared"], s["is_minor"]) for s in mine] == [(world["sid"], False, False)]
    assert seeded.get("/api/facilitator/students", headers=other).json() == []
    assert seeded.get("/api/facilitator/students", headers=world["student"]).status_code == 403


@pytest.mark.parametrize(("method", "suffix", "body"), STUDENT_ENDPOINTS)
def test_an_unassigned_facilitator_gets_not_found_for_everything(
    seeded, db, world, method, suffix, body
):
    stranger = staff_headers(seeded, db, "facilitator", "9100000051")
    r = call(seeded, method, url(world["sid"], suffix), stranger, body)
    assert r.status_code == 404 and r.json()["detail"] == "not_found"
    unknown = call(seeded, method, url(uuid.uuid4(), suffix), stranger, body)
    assert unknown.json() == r.json()  # an unknown student looks exactly like an unassigned one


@pytest.mark.parametrize(("method", "suffix", "body"), STUDENT_ENDPOINTS)
def test_an_assigned_facilitator_is_blocked_until_the_student_shares(
    seeded, facilitator, world, method, suffix, body
):
    r = call(seeded, method, url(world["sid"], suffix), facilitator, body)
    assert (r.status_code, r.json()["detail"]) == (403, "student_has_not_shared")


def test_sharing_can_be_granted_and_withdrawn_by_the_student(seeded, facilitator, world):
    student = world["student"]
    assert seeded.get("/api/consents/facilitator-access", headers=student).json()["active"] is None
    share_with_facilitators(seeded, student)
    assert seeded.get(url(world["sid"], "/profile"), headers=facilitator).status_code == 200
    assert seeded.get("/api/facilitator/students", headers=facilitator).json()[0]["shared"] is True
    assert (
        seeded.post("/api/consents/facilitator-access/withdraw", headers=student).status_code == 204
    )
    assert seeded.get(url(world["sid"], "/profile"), headers=facilitator).status_code == 403


def test_sharing_for_a_minor_needs_the_guardian(seeded, admin, facilitator):
    minor = make_student(seeded, phone="9200000002", dob=MINOR_DOB)
    assign(seeded, admin, facilitator, minor)
    own = seeded.post("/api/consents/facilitator-access", json={"given_by": "self"}, headers=minor)
    assert own.status_code == 422
    share_with_facilitators(seeded, minor, minor=True)
    sid = user_id(seeded, minor)
    assert (
        seeded.get(url(sid, "/profile"), headers=facilitator).json()["student"]["is_minor"] is True
    )


def test_a_student_with_a_data_consent_only_has_no_facilitator_access_by_default(
    seeded, db, admin, facilitator
):
    student = make_student(seeded, phone="9200000003")
    assign(seeded, admin, facilitator, student)
    assert (
        seeded.get(url(user_id(seeded, student), "/profile"), headers=facilitator).status_code
        == 403
    )


def test_ending_the_assignment_cuts_access_at_once(seeded, admin, facilitator, world):
    share_with_facilitators(seeded, world["student"])
    [row] = seeded.get("/api/admin/assignments", headers=admin).json()
    assert seeded.get(url(world["sid"], "/profile"), headers=facilitator).status_code == 200
    seeded.delete(f"/api/admin/assignments/{row['id']}", headers=admin)
    assert seeded.get(url(world["sid"], "/profile"), headers=facilitator).status_code == 404


def test_viewing_a_profile_is_audited_with_who_and_whom(seeded, db, facilitator, world):
    share_with_facilitators(seeded, world["student"])
    seeded.get(url(world["sid"], "/profile"), headers=facilitator)
    [event] = db.scalars(
        select(AuditEvent).where(AuditEvent.action == "facilitator.viewed_profile")
    ).all()
    assert (
        str(event.actor_id) == user_id(seeded, facilitator)
        and str(event.subject_user_id) == world["sid"]
    )
    assert event.detail is None  # no profile content in the log


def test_observations_keep_provenance_and_never_overwrite_what_the_student_said(
    seeded, db, facilitator, world
):
    student, sid = world["student"], world["sid"]
    seeded.put("/api/profile/fields/skills", json={"value": ["cooking"]}, headers=student)
    share_with_facilitators(seeded, student)
    r = seeded.post(
        url(sid, "/observations"),
        json={
            "key": "skills",
            "value": ["wiring"],
            "basis": "Fixed a switch board in class",
            "verified": True,
        },
        headers=facilitator,
    )
    assert r.status_code == 201
    seeded.post(
        url(sid, "/observations"),
        json={
            "key": "skills",
            "value": ["drawing"],
            "provenance": "hypothesis",
            "basis": "Doodles in every notebook",
        },
        headers=facilitator,
    )
    view = seeded.get(url(sid, "/profile"), headers=facilitator).json()
    skills = next(f for f in view["fields"] if f["key"] == "skills")
    by = {e["provenance"]: e for e in skills["entries"]}
    assert by["reported"]["value"] == ["cooking"] and by["reported"]["source"] == "student_form"
    assert by["observed"]["value"] == ["wiring"] and by["observed"]["verification"] == "verified"
    assert by["observed"]["source"] == f"facilitator:{user_id(seeded, facilitator)}"
    assert by["observed"]["basis"] == "Fixed a switch board in class"
    assert by["hypothesis"]["value"] == ["drawing"]
    # The student sees all of it on their own profile too (no hidden notes).
    mine = next(
        f
        for f in seeded.get("/api/profile", headers=student).json()["fields"]
        if f["key"] == "skills"
    )
    assert {e["provenance"] for e in mine["entries"]} == {"reported", "observed", "hypothesis"}


def test_observations_need_a_basis_and_valid_data(seeded, facilitator, world):
    share_with_facilitators(seeded, world["student"])
    sid = world["sid"]
    for body, code in (
        ({"key": "skills", "value": ["x"], "basis": ""}, 422),
        ({"key": "skills", "value": "not-a-list", "basis": "Saw it"}, 422),
        ({"key": "blood_group", "value": "O", "basis": "Saw it"}, 404),
        ({"key": "skills", "value": ["x"], "provenance": "reported", "basis": "Saw it"}, 422),
    ):
        assert (
            seeded.post(url(sid, "/observations"), json=body, headers=facilitator).status_code
            == code
        )


def test_assisted_answers_are_recorded_as_the_students_own_with_the_helper_named(
    seeded, facilitator, world
):
    share_with_facilitators(seeded, world["student"])
    sid = world["sid"]
    seeded.post(
        url(sid, "/assisted-answers"),
        json={"key": "education_stage", "value": "class_10"},
        headers=facilitator,
    )
    seeded.post(
        url(sid, "/assisted-answers"),
        json={"key": "district", "unknown": True},
        headers=facilitator,
    )
    fields = {
        f["key"]: f for f in seeded.get("/api/profile", headers=world["student"]).json()["fields"]
    }
    stage = fields["education_stage"]["entries"][0]
    assert stage["provenance"] == "reported" and stage["source"].startswith("assisted_by:")
    assert fields["district"]["entries"][0]["provenance"] == "unknown"
    bad = seeded.post(url(sid, "/assisted-answers"), json={"key": "district"}, headers=facilitator)
    assert bad.status_code == 422


def test_recommendations_can_be_reviewed_and_the_review_must_match_the_run(
    seeded, db, facilitator, world
):
    student, sid = world["student"], world["sid"]
    seeded.put("/api/profile/fields/interests", json={"value": ["wiring"]}, headers=student)
    share_with_facilitators(seeded, student)
    assert seeded.get(url(sid, "/recommendations/latest"), headers=facilitator).status_code == 404
    run = seeded.post("/api/recommendations", json={}, headers=student).json()
    seen = seeded.get(url(sid, "/recommendations/latest"), headers=facilitator).json()
    assert seen["id"] == run["id"] and seen["items"][0]["career"]["slug"] == "electrician"
    ok = seeded.post(
        url(sid, "/recommendations/review"),
        json={
            "run_id": run["id"],
            "career": "electrician",
            "decision": "agree",
            "note": "Good fit, saw his work",
        },
        headers=facilitator,
    )
    assert ok.status_code == 201 and ok.json()["decision"] == "agree"
    wrong = seeded.post(
        url(sid, "/recommendations/review"),
        json={"run_id": run["id"], "career": "nurse", "decision": "agree"},
        headers=facilitator,
    )
    assert wrong.status_code == 404
    assert (
        seeded.post(
            url(sid, "/recommendations/review"),
            json={"run_id": run["id"], "career": "electrician", "decision": "maybe"},
            headers=facilitator,
        ).status_code
        == 422
    )


def test_endorsements_reach_the_student_who_can_mark_them(seeded, db, facilitator, world):
    student, sid = world["student"], world["sid"]
    share_with_facilitators(seeded, student)
    r = seeded.post(
        url(sid, "/endorsements"),
        json={"opportunity": "fresh-scholarship", "note": "Top marks in maths"},
        headers=facilitator,
    )
    assert r.status_code == 201 and r.json()["status"] == "suggested"
    mine = seeded.get("/api/me/endorsements", headers=student).json()
    assert [(e["opportunity_slug"], e["note"]) for e in mine] == [
        ("fresh-scholarship", "Top marks in maths")
    ]
    seen = seeded.put(
        f"/api/me/endorsements/{mine[0]['id']}", json={"status": "seen"}, headers=student
    )
    assert seen.json()["status"] == "seen"
    assert (
        seeded.put(
            f"/api/me/endorsements/{mine[0]['id']}", json={"status": "accepted"}, headers=student
        ).status_code
        == 422
    )
    assert (
        seeded.post(
            url(sid, "/endorsements"), json={"opportunity": "ghost"}, headers=facilitator
        ).status_code
        == 404
    )
    other = make_student(seeded, phone="9200000004")
    assert (
        seeded.put(
            f"/api/me/endorsements/{mine[0]['id']}", json={"status": "dismissed"}, headers=other
        ).status_code
        == 404
    )


def test_facilitators_can_support_pathway_progress_under_the_same_rules(seeded, facilitator, world):
    student, sid = world["student"], world["sid"]
    seeded.put("/api/profile/fields/education_stage", json={"value": "class_9"}, headers=student)
    share_with_facilitators(seeded, student)
    plan = seeded.post("/api/pathways", json={"career": "electrician"}, headers=student).json()
    listed = seeded.get(url(sid, "/pathways"), headers=facilitator).json()
    assert [p["id"] for p in listed] == [plan["id"]]
    base = url(sid, f"/pathways/{plan['id']}/steps")
    blocked = seeded.put(f"{base}/route:0", json={"status": "in_progress"}, headers=facilitator)
    assert (blocked.status_code, blocked.json()["detail"]) == (409, "prerequisites_not_done")
    done = seeded.put(
        f"{base}/stage:class_10",
        json={"status": "done", "note": "Marksheet seen"},
        headers=facilitator,
    )
    assert done.status_code == 200
    step = next(s for s in done.json()["steps"] if s["id"] == "stage:class_10")
    assert step["status"] == "done" and step["note"] == "Marksheet seen"
    assert (
        seeded.put(f"{base}/nope", json={"status": "done"}, headers=facilitator).status_code == 404
    )


def test_help_requests_flow_from_student_to_assigned_facilitator_only(
    seeded, db, facilitator, world
):
    student = world["student"]  # has NOT shared the profile: asking for help is still allowed
    r = seeded.post(
        "/api/me/help-requests",
        json={"topic": "interview", "message": "I need help answering"},
        headers=student,
    )
    assert r.status_code == 201
    stranger = staff_headers(seeded, db, "facilitator", "9100000052")
    assert seeded.get("/api/facilitator/help-requests", headers=stranger).json() == []
    [req] = seeded.get("/api/facilitator/help-requests", headers=facilitator).json()
    assert req["topic"] == "interview" and req["student_id"] == world["sid"]
    assert (
        seeded.get("/api/facilitator/students", headers=facilitator).json()[0]["open_help_requests"]
        == 1
    )
    assert (
        seeded.post(
            f"/api/facilitator/help-requests/{req['id']}/resolve", headers=stranger
        ).status_code
        == 404
    )
    done = seeded.post(f"/api/facilitator/help-requests/{req['id']}/resolve", headers=facilitator)
    assert done.json()["status"] == "resolved"
    assert seeded.get("/api/facilitator/help-requests", headers=facilitator).json() == []


def test_students_can_see_who_is_assigned_to_them(seeded, facilitator, world):
    [f] = seeded.get("/api/me/facilitators", headers=world["student"]).json()
    assert f["display_name"] == "Facilitator"


def test_no_facilitator_action_ever_changes_the_students_reported_values(
    seeded, db, facilitator, world
):
    student, sid = world["student"], world["sid"]
    seeded.put("/api/profile/fields/education_stage", json={"value": "class_10"}, headers=student)
    share_with_facilitators(seeded, student)
    seeded.post(
        url(sid, "/observations"),
        json={"key": "education_stage", "value": "class_12", "basis": "Looks older"},
        headers=facilitator,
    )
    reported = [
        e
        for e in db.scalars(select(ProfileEntry))
        if e.provenance.value == "reported" and e.superseded_at is None
    ]
    assert [e.value for e in reported] == ["class_10"]
