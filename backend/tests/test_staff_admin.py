import pytest

from app.admin import cli
from app.modules.identity import service
from app.modules.identity.models import Role
from tests.conftest import STAFF_PIN, assign, make_student, staff_headers, user_id


def test_staff_pins_must_be_six_to_twelve_digits(db):
    for pin in ("1234", "12345", "1234567890123", "12ab5678", ""):
        with pytest.raises(service.WeakStaffPin):
            service.create_staff_user(db, Role.FACILITATOR, "9100000009", pin, "X", None)
    assert (
        service.create_staff_user(db, Role.FACILITATOR, "9100000009", "123456", "X", None).role
        is Role.FACILITATOR
    )
    with pytest.raises(service.PhoneAlreadyRegistered):
        service.create_staff_user(db, Role.PARTNER, "9100000009", STAFF_PIN, "Y", None)
    with pytest.raises(ValueError):
        service.create_staff_user(db, Role.STUDENT, "9100000008", STAFF_PIN, "Z", None)


def test_staff_login_with_a_long_pin_and_wrong_pin_is_refused(seeded, db):
    staff_headers(seeded, db, "facilitator", "9100000020")
    bad = seeded.post("/api/auth/login", json={"phone": "9100000020", "pin": "87654321"})
    assert bad.status_code == 401
    assert (
        seeded.get(
            "/api/me", headers=staff_headers(seeded, db, "partner", "9100000021")
        ).status_code
        == 200
    )


def test_students_cannot_register_with_the_long_staff_style_pin(seeded):
    from tests.conftest import register

    assert register(seeded, pin="12345678").status_code == 422


def test_cli_creates_a_user_and_reports_problems(seeded, db, monkeypatch, capsys, settings):
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    assert (
        cli.main(
            [
                "create-user",
                "--role",
                "admin",
                "--phone",
                "9100000030",
                "--name",
                "Root",
                "--pin",
                STAFF_PIN,
            ]
        )
        == 0
    )
    assert "created admin" in capsys.readouterr().out
    assert (
        cli.main(
            [
                "create-user",
                "--role",
                "admin",
                "--phone",
                "9100000030",
                "--name",
                "Root",
                "--pin",
                STAFF_PIN,
            ]
        )
        == 1
    )
    assert "already has an account" in capsys.readouterr().err
    assert (
        cli.main(
            [
                "create-user",
                "--role",
                "admin",
                "--phone",
                "9100000031",
                "--name",
                "R",
                "--pin",
                "123",
            ]
        )
        == 1
    )
    assert "6 to 12 digits" in capsys.readouterr().err
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: STAFF_PIN)
    assert (
        cli.main(["create-user", "--role", "partner", "--phone", "9100000032", "--name", "P"]) == 0
    )


def test_only_admins_reach_admin_endpoints(seeded, admin, facilitator, partner):
    student = make_student(seeded)
    assert seeded.get("/api/admin/users").status_code == 401
    for headers in (student, facilitator, partner):
        assert seeded.get("/api/admin/users", headers=headers).status_code == 403
        assert seeded.post("/api/admin/assignments", json={}, headers=headers).status_code == 403
    assert seeded.get("/api/admin/users", headers=admin).status_code == 200


def test_admin_creates_facilitators_and_partners_but_never_other_admins(seeded, admin):
    body = {
        "role": "facilitator",
        "phone": "9100000040",
        "pin": "123456789",
        "display_name": "Meena",
    }
    created = seeded.post("/api/admin/users", json=body, headers=admin)
    assert created.status_code == 201 and created.json()["role"] == "facilitator"
    assert "pin" not in str(created.json()).lower()
    assert seeded.post("/api/admin/users", json=body, headers=admin).status_code == 409
    assert (
        seeded.post(
            "/api/admin/users", json={**body, "role": "admin", "phone": "9100000041"}, headers=admin
        ).status_code
        == 422
    )
    assert (
        seeded.post(
            "/api/admin/users", json={**body, "pin": "1234", "phone": "9100000042"}, headers=admin
        ).status_code
        == 422
    )
    listed = seeded.get("/api/admin/users?role=facilitator", headers=admin).json()
    assert [u["display_name"] for u in listed] == ["Meena"]
    # The new facilitator can log in.
    assert (
        seeded.post("/api/auth/login", json={"phone": "9100000040", "pin": "123456789"}).status_code
        == 200
    )


def test_assignments_validate_roles_reject_duplicates_and_can_end(
    seeded, admin, facilitator, partner
):
    student = make_student(seeded)
    row = assign(seeded, admin, facilitator, student)
    again = seeded.post(
        "/api/admin/assignments",
        json={
            "facilitator_id": user_id(seeded, facilitator),
            "student_id": user_id(seeded, student),
        },
        headers=admin,
    )
    assert (again.status_code, again.json()["detail"]) == (409, "already_assigned")
    bad = seeded.post(
        "/api/admin/assignments",
        json={"facilitator_id": user_id(seeded, partner), "student_id": user_id(seeded, student)},
        headers=admin,
    )
    assert bad.status_code == 422
    ended = seeded.delete(f"/api/admin/assignments/{row['id']}", headers=admin)
    assert ended.status_code == 200 and ended.json()["ended_at"] is not None
    # Re-assigning after it ended is allowed.
    assign(seeded, admin, facilitator, student)
    assert len(seeded.get("/api/admin/assignments", headers=admin).json()) == 2
    assert (
        seeded.delete(
            "/api/admin/assignments/00000000-0000-0000-0000-000000000000", headers=admin
        ).status_code
        == 404
    )
