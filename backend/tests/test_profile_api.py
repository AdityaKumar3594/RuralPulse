from sqlalchemy import select

from app.core.audit import AuditEvent
from app.modules.profile.models import ProfileEntry
from tests.conftest import GUARDIAN, MINOR_DOB, auth_headers, register


def field(profile, key):
    return next(f for f in profile["fields"] if f["key"] == key)


def test_profile_requires_consent(client_with_db):
    h = auth_headers(register(client_with_db))
    r = client_with_db.get("/api/profile", headers=h)
    assert r.status_code == 403
    assert r.json()["detail"] == "consent_required"
    r = client_with_db.put("/api/profile/fields/interests", json={"value": ["x"]}, headers=h)
    assert r.status_code == 403


def test_minor_with_only_self_style_access_is_blocked_until_guardian_consents(client_with_db):
    h = auth_headers(register(client_with_db, dob=MINOR_DOB))
    assert client_with_db.get("/api/profile", headers=h).status_code == 403
    client_with_db.post("/api/consents", json=GUARDIAN, headers=h)
    assert client_with_db.get("/api/profile", headers=h).status_code == 200


def test_withdrawn_consent_blocks_profile_again(client_with_db, adult):
    assert client_with_db.get("/api/profile", headers=adult).status_code == 200
    client_with_db.post("/api/consents/withdraw", headers=adult)
    assert client_with_db.get("/api/profile", headers=adult).status_code == 403


def test_empty_profile_is_all_unknown_not_negative(client_with_db, adult):
    profile = client_with_db.get("/api/profile", headers=adult).json()
    assert profile["fields"]
    assert all(f["state"] == "unknown" and f["entries"] == [] for f in profile["fields"])


def test_reported_value_is_stored_with_provenance(client_with_db, adult):
    r = client_with_db.put(
        "/api/profile/fields/interests", json={"value": ["farming"]}, headers=adult
    )
    assert r.status_code == 200
    f = field(r.json(), "interests")
    assert f["state"] == "established"
    [entry] = f["entries"]
    assert entry["provenance"] == "reported"
    assert entry["verification"] == "unverified"
    assert entry["source"] == "student_form"
    assert entry["value"] == ["farming"]


def test_student_can_say_unknown_and_correct_later(client_with_db, adult):
    put = lambda body: client_with_db.put(  # noqa: E731
        "/api/profile/fields/education_stage", json=body, headers=adult
    )
    f = field(put({"unknown": True}).json(), "education_stage")
    assert f["state"] == "unknown"
    assert [e["provenance"] for e in f["entries"]] == ["unknown"]

    f = field(put({"value": "class_10"}).json(), "education_stage")
    assert f["state"] == "established"
    assert [e["provenance"] for e in f["entries"]] == ["reported"]

    f = field(put({"value": "class_11"}).json(), "education_stage")
    assert [e["value"] for e in f["entries"]] == ["class_11"]


def test_corrections_keep_history(client_with_db, adult, db):
    for stage in ("class_10", "class_11"):
        client_with_db.put(
            "/api/profile/fields/education_stage", json={"value": stage}, headers=adult
        )
    rows = db.scalars(select(ProfileEntry).order_by(ProfileEntry.created_at)).all()
    assert [r.value for r in rows] == ["class_10", "class_11"]
    assert rows[0].superseded_at is not None
    assert rows[1].superseded_at is None


def test_invalid_input_is_rejected(client_with_db, adult):
    def put(key, body):
        return client_with_db.put(f"/api/profile/fields/{key}", json=body, headers=adult)

    assert put("education_stage", {"value": "phd"}).status_code == 422
    assert put("nonexistent", {"value": "x"}).status_code == 404
    assert put("interests", {}).status_code == 422  # neither value nor unknown
    assert put("interests", {"value": ["a"], "unknown": True}).status_code == 422


def test_students_only_see_their_own_profile(client_with_db, adult):
    other = auth_headers(register(client_with_db, phone="9000000001"))
    client_with_db.post("/api/consents", json={"given_by": "self"}, headers=other)
    client_with_db.put("/api/profile/fields/interests", json={"value": ["secret"]}, headers=adult)
    theirs = client_with_db.get("/api/profile", headers=other).json()
    assert field(theirs, "interests")["entries"] == []


def test_profile_audit_logs_key_but_not_value(client_with_db, adult, db):
    client_with_db.put(
        "/api/profile/fields/interests", json={"value": ["private-hobby"]}, headers=adult
    )
    events = db.scalars(
        select(AuditEvent).where(AuditEvent.action == "profile.entry_recorded")
    ).all()
    assert len(events) == 1
    assert events[0].detail == {"key": "interests", "provenance": "reported"}
