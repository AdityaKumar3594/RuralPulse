from datetime import date

from sqlalchemy import select

from app.core.audit import AuditEvent
from app.modules.identity.models import User
from app.modules.identity.service import age_on, is_minor
from tests.conftest import ADULT_DOB, GUARDIAN, MINOR_DOB, auth_headers, register


def test_age_boundaries():
    assert age_on(date(2008, 10, 18), date(2026, 10, 17)) == 17
    assert age_on(date(2008, 10, 18), date(2026, 10, 18)) == 18
    assert is_minor(User(date_of_birth=None))  # unknown age is treated as minor


def test_register_returns_token_and_never_exposes_pin(client_with_db, db):
    r = register(client_with_db)
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["role"] == "student"
    assert "pin" not in str(body).lower().replace("pin_", "")
    stored = db.scalar(select(User))
    assert stored.pin_hash != "1234"
    assert client_with_db.get("/api/me", headers=auth_headers(r)).json()["id"] == body["user"]["id"]


def test_register_validation(client_with_db):
    assert register(client_with_db, phone="12345").status_code == 422
    assert register(client_with_db, phone="5876543210").status_code == 422  # must start 6-9
    assert register(client_with_db, pin="12").status_code == 422
    assert register(client_with_db, pin="abcd").status_code == 422
    assert register(client_with_db, dob="2099-01-01").status_code == 422
    assert register(client_with_db, dob="1900-01-01").status_code == 422


def test_duplicate_phone_is_rejected(client_with_db):
    assert register(client_with_db).status_code == 201
    assert register(client_with_db).status_code == 409


def test_login_success_and_uniform_failure(client_with_db):
    register(client_with_db)
    ok = client_with_db.post("/api/auth/login", json={"phone": "9876543210", "pin": "1234"})
    assert ok.status_code == 200
    wrong_pin = client_with_db.post("/api/auth/login", json={"phone": "9876543210", "pin": "9999"})
    no_user = client_with_db.post("/api/auth/login", json={"phone": "9000000000", "pin": "1234"})
    assert wrong_pin.status_code == no_user.status_code == 401
    assert wrong_pin.json() == no_user.json()


def test_account_locks_after_repeated_failures_even_with_correct_pin(client_with_db):
    register(client_with_db)
    bad = {"phone": "9876543210", "pin": "9999"}
    for _ in range(5):
        assert client_with_db.post("/api/auth/login", json=bad).status_code == 401
    good = {"phone": "9876543210", "pin": "1234"}
    assert client_with_db.post("/api/auth/login", json=good).status_code == 429


def test_protected_routes_need_a_valid_token(client_with_db):
    assert client_with_db.get("/api/me").status_code == 401
    bad = {"Authorization": "Bearer nonsense"}
    assert client_with_db.get("/api/me", headers=bad).status_code == 401
    assert client_with_db.get("/api/profile", headers=bad).status_code == 401


def test_adult_must_consent_for_self_and_minor_through_guardian(client_with_db):
    adult = auth_headers(register(client_with_db))
    minor = auth_headers(register(client_with_db, phone="9876543211", dob=MINOR_DOB))

    assert (
        client_with_db.get("/api/consents/me", headers=adult).json()["required_given_by"] == "self"
    )
    assert (
        client_with_db.get("/api/consents/me", headers=minor).json()["required_given_by"]
        == "guardian"
    )
    # Wrong giver in either direction is refused.
    assert client_with_db.post("/api/consents", json=GUARDIAN, headers=adult).status_code == 422
    r = client_with_db.post("/api/consents", json={"given_by": "self"}, headers=minor)
    assert r.status_code == 422
    r = client_with_db.post("/api/consents", json=GUARDIAN, headers=minor)
    assert r.status_code == 201
    assert r.json()["verification"] == "self_declared"  # guardian identity is not verified


def test_guardian_consent_requires_guardian_details(client_with_db):
    minor = auth_headers(register(client_with_db, dob=MINOR_DOB))
    body = {"given_by": "guardian", "guardian_name": "Parent"}
    assert client_with_db.post("/api/consents", json=body, headers=minor).status_code == 422


def test_consent_withdrawal_and_regrant(client_with_db):
    h = auth_headers(register(client_with_db, dob=ADULT_DOB))
    assert (
        client_with_db.post("/api/consents", json={"given_by": "self"}, headers=h).status_code
        == 201
    )
    assert client_with_db.post("/api/consents/withdraw", headers=h).status_code == 204
    assert client_with_db.get("/api/consents/me", headers=h).json()["active"] is None
    assert (
        client_with_db.post("/api/consents", json={"given_by": "self"}, headers=h).status_code
        == 201
    )
    assert client_with_db.get("/api/consents/me", headers=h).json()["active"] is not None


def test_audit_events_are_written_without_secrets(client_with_db, db):
    h = auth_headers(register(client_with_db))
    client_with_db.post("/api/consents", json={"given_by": "self"}, headers=h)
    events = db.scalars(select(AuditEvent)).all()
    assert {e.action for e in events} == {"user.registered", "consent.granted"}
    assert "1234" not in str([e.detail for e in events])
