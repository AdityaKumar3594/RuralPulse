import pytest

from tests.conftest import assign, make_student, share_with_facilitators, staff_headers, user_id


@pytest.fixture
def student(seeded):
    return make_student(seeded)


def save(client, headers, slug="document-scheme"):
    r = client.post("/api/applications", json={"opportunity": slug}, headers=headers)
    assert r.status_code in (200, 201), r.text
    return r.json()


def put(client, headers, app_id, **body):
    return client.put(f"/api/applications/{app_id}", json=body, headers=headers)


def advance_to_applied(client, headers, app_id):
    assert put(client, headers, app_id, internal_status="preparing").status_code == 200
    put(client, headers, app_id, documents={"Income certificate": True, "Photo ID": True})
    assert put(client, headers, app_id, internal_status="documents_ready").status_code == 200
    r = put(client, headers, app_id, internal_status="applied")
    assert r.status_code == 200
    return r.json()


def test_requires_login_and_consent(seeded):
    assert (
        seeded.post("/api/applications", json={"opportunity": "document-scheme"}).status_code == 401
    )
    from tests.conftest import auth_headers, register

    h = auth_headers(register(seeded))
    assert seeded.get("/api/applications", headers=h).status_code == 403


def test_saving_is_idempotent_snapshots_documents_and_hides_nothing(seeded, student):
    first = seeded.post(
        "/api/applications", json={"opportunity": "document-scheme"}, headers=student
    )
    assert first.status_code == 201
    app = first.json()
    assert app["internal_status"] == "saved" and app["documents"] == {
        "Income certificate": False,
        "Photo ID": False,
    }
    assert app["external_status"] == "unknown" and app["external_confirmed"] is False
    assert len(app["reference_code"]) == 8 and app["reference_code"].isalnum()
    again = seeded.post(
        "/api/applications", json={"opportunity": "document-scheme"}, headers=student
    )
    assert again.status_code == 200 and again.json()["id"] == app["id"]
    assert len(seeded.get("/api/applications", headers=student).json()) == 1
    assert (
        seeded.post("/api/applications", json={"opportunity": "ghost"}, headers=student).status_code
        == 404
    )


def test_internal_status_follows_the_allowed_transitions(seeded, student):
    app = save(seeded, student)
    # Cannot jump straight to "applied" from "saved".
    r = put(seeded, student, app["id"], internal_status="applied")
    assert (r.status_code, r.json()["detail"]) == (409, "invalid_transition")
    assert put(seeded, student, app["id"], internal_status="preparing").status_code == 200
    # Documents must all be ticked before "documents ready".
    r = put(seeded, student, app["id"], internal_status="documents_ready")
    assert (r.status_code, r.json()["detail"]) == (409, "documents_not_ready")
    r = put(seeded, student, app["id"], internal_status="applied")
    assert (r.status_code, r.json()["detail"]) == (409, "documents_not_ready")
    put(seeded, student, app["id"], documents={"Income certificate": True})
    assert put(seeded, student, app["id"], internal_status="documents_ready").status_code == 409
    put(seeded, student, app["id"], documents={"Photo ID": True})
    assert put(seeded, student, app["id"], internal_status="documents_ready").status_code == 200
    applied = put(seeded, student, app["id"], internal_status="applied").json()
    assert applied["internal_status"] == "applied"
    # Once applied, the only way out is withdrawing; then saving again restarts.
    assert put(seeded, student, app["id"], internal_status="preparing").status_code == 409
    assert put(seeded, student, app["id"], internal_status="withdrawn").status_code == 200
    resaved = seeded.post(
        "/api/applications", json={"opportunity": "document-scheme"}, headers=student
    )
    assert resaved.json()["internal_status"] == "saved"


def test_an_opportunity_without_documents_can_go_from_preparing_to_applied(seeded, student):
    app = save(seeded, student, "fresh-scholarship")
    put(seeded, student, app["id"], internal_status="preparing")
    assert put(seeded, student, app["id"], internal_status="applied").status_code == 200


def test_unknown_documents_and_empty_updates_are_rejected(seeded, student):
    app = save(seeded, student)
    r = put(seeded, student, app["id"], documents={"Passport": True})
    assert (r.status_code, r.json()["detail"]) == (409, "unknown_document")
    assert put(seeded, student, app["id"]).status_code == 422
    assert put(seeded, student, app["id"], internal_status="finished").status_code == 422


def test_a_student_report_is_never_presented_as_confirmed(seeded, student):
    app = save(seeded, student)
    r = put(seeded, student, app["id"], reported_external_status="accepted")
    assert (r.status_code, r.json()["detail"]) == (409, "not_applied_yet")
    advance_to_applied(seeded, student, app["id"])
    reported = put(seeded, student, app["id"], reported_external_status="under_review").json()
    assert reported["external_status"] == "under_review"
    assert reported["external_status_source"] == "student_reported"
    assert reported["external_confirmed"] is False  # only confirmed statuses may be shown as fact
    cleared = put(seeded, student, app["id"], reported_external_status="unknown").json()
    assert cleared["external_status_source"] is None


def test_a_facilitator_confirmation_is_confirmed_and_students_cannot_override_it(
    seeded, db, admin, student
):
    facilitator = staff_headers(seeded, db, "facilitator", "9100000060")
    assign(seeded, admin, facilitator, student)
    share_with_facilitators(seeded, student)
    app = save(seeded, student)
    advance_to_applied(seeded, student, app["id"])
    seen = seeded.get(
        f"/api/facilitator/students/{user_id(seeded, student)}/applications", headers=facilitator
    ).json()
    assert [a["id"] for a in seen] == [app["id"]]
    ok = seeded.post(
        f"/api/facilitator/applications/{app['id']}/confirm",
        json={"status": "submitted", "note": "Saw the acknowledgement SMS"},
        headers=facilitator,
    )
    body = ok.json()
    assert ok.status_code == 200 and body["external_confirmed"] is True
    assert body["external_status_source"] == "facilitator_confirmed"
    assert body["external_status_note"] == "Saw the acknowledgement SMS"
    r = put(seeded, student, app["id"], reported_external_status="accepted")
    assert (r.status_code, r.json()["detail"]) == (409, "already_confirmed")
    mine = seeded.get(f"/api/applications/{app['id']}", headers=student).json()
    assert mine["external_status"] == "submitted" and mine["external_confirmed"] is True


def test_facilitator_confirmation_follows_the_assignment_and_sharing_rules(
    seeded, db, admin, student
):
    facilitator = staff_headers(seeded, db, "facilitator", "9100000061")
    stranger = staff_headers(seeded, db, "facilitator", "9100000062")
    app = save(seeded, student)
    advance_to_applied(seeded, student, app["id"])
    body = {"status": "submitted"}
    assert (
        seeded.post(
            f"/api/facilitator/applications/{app['id']}/confirm", json=body, headers=stranger
        ).status_code
        == 404
    )
    assign(seeded, admin, facilitator, student)
    r = seeded.post(
        f"/api/facilitator/applications/{app['id']}/confirm", json=body, headers=facilitator
    )
    assert (r.status_code, r.json()["detail"]) == (403, "student_has_not_shared")
    share_with_facilitators(seeded, student)
    assert (
        seeded.post(
            f"/api/facilitator/applications/{app['id']}/confirm",
            json={"status": "winner"},
            headers=facilitator,
        ).status_code
        == 422
    )


def test_applications_are_private_and_help_can_be_requested(seeded, db, admin, student):
    app = save(seeded, student)
    other = make_student(seeded, phone="9200000005")
    assert seeded.get(f"/api/applications/{app['id']}", headers=other).status_code == 404
    assert put(seeded, other, app["id"], note="x").status_code == 404
    assert seeded.get("/api/applications", headers=other).json() == []
    r = seeded.post(
        f"/api/applications/{app['id']}/help",
        json={"message": "Which form is this?"},
        headers=student,
    )
    assert r.status_code == 201 and r.json()["status"] == "open"
    facilitator = staff_headers(seeded, db, "facilitator", "9100000063")
    assign(seeded, admin, facilitator, student)
    [req] = seeded.get("/api/facilitator/help-requests", headers=facilitator).json()
    assert req["topic"] == "application" and req["opportunity_slug"] == "document-scheme"
    assert (
        seeded.post(f"/api/applications/{app['id']}/help", json={}, headers=other).status_code
        == 404
    )
