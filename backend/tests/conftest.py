import os
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import Settings
from app.core.db import Base, check_database, make_engine
from app.main import create_app

# Nothing listens on port 1, so connections fail fast without depending on the network.
UNREACHABLE_DB_URL = "postgresql+psycopg://Ruralpulse:Ruralpulse@127.0.0.1:1/Ruralpulse"

ADULT_DOB = (date.today() - timedelta(days=365 * 25 + 7)).isoformat()
MINOR_DOB = (date.today() - timedelta(days=365 * 15 + 4)).isoformat()


def make_settings(**overrides) -> Settings:
    # _env_file=None keeps tests independent of a developer's backend/.env.
    return Settings(_env_file=None, app_env="test", **overrides)


@pytest.fixture
def client_without_db() -> TestClient:
    app = create_app(make_settings(database_url=UNREACHABLE_DB_URL, db_connect_timeout_seconds=1))
    return TestClient(app)


@pytest.fixture(scope="session")
def test_db_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    # Tests TRUNCATE every table, so refuse anything that isn't clearly a test database.
    if not url.rsplit("/", 1)[-1].endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must point at a database whose name ends in '_test'")
    if not check_database(make_engine(make_settings(database_url=url))):
        pytest.fail("TEST_DATABASE_URL is set but the database is unreachable")
    # Build the schema from the real migrations, which also verifies them.
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return url


@pytest.fixture
def settings(test_db_url) -> Settings:
    return make_settings(database_url=test_db_url)


@pytest.fixture
def client_with_db(settings) -> Iterator[TestClient]:
    app = create_app(settings)
    yield TestClient(app)
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with app.state.engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))  # noqa: S608
    app.state.engine.dispose()


@pytest.fixture
def db(client_with_db):
    session = client_with_db.app.state.session_factory()
    yield session
    session.close()


def register(client: TestClient, phone="9876543210", dob=ADULT_DOB, pin="1234", **extra):
    body = {"display_name": "Test Student", "phone": phone, "pin": pin, "date_of_birth": dob}
    return client.post("/api/auth/register", json=body | extra)


def auth_headers(response) -> dict[str, str]:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


GUARDIAN = {"given_by": "guardian", "guardian_name": "Parent", "guardian_phone": "9123456789"}


@pytest.fixture
def adult(client_with_db):
    """An adult student who has given self-consent."""
    headers = auth_headers(register(client_with_db))
    assert client_with_db.post(
        "/api/consents", json={"given_by": "self"}, headers=headers
    ).is_success
    return headers


FIXTURE_SEED = Path(__file__).parent / "fixtures" / "seed"


@pytest.fixture
def seeded(client_with_db, db):
    """The deterministic fixture dataset loaded into the test database (never production data)."""
    from app.ingestion.bundle import load_bundle
    from app.ingestion.loader import upsert_bundle

    upsert_bundle(db, load_bundle(FIXTURE_SEED))
    # Fixture dates are fixed, but "fresh" is relative to the real date; keep tests stable over
    # time by treating every verified fixture record as checked today.
    db.execute(
        text(
            "UPDATE opportunities SET verified_at = CURRENT_DATE WHERE verified_at >= '2026-01-01'"
        )
    )
    db.commit()
    return client_with_db


STAFF_PIN = "12345678"


def staff_headers(client, db, role: str, phone: str, name: str | None = None):
    """Create a staff account directly (they are never self-service) and log it in."""
    from app.modules.identity import service
    from app.modules.identity.models import Role

    service.create_staff_user(db, Role(role), phone, STAFF_PIN, name or role.title(), None)
    response = client.post("/api/auth/login", json={"phone": phone, "pin": STAFF_PIN})
    assert response.status_code == 200, response.text
    return auth_headers(response)


@pytest.fixture
def admin(seeded, db):
    return staff_headers(seeded, db, "admin", "9100000001")


@pytest.fixture
def facilitator(seeded, db):
    return staff_headers(seeded, db, "facilitator", "9100000002")


@pytest.fixture
def partner(seeded, db):
    return staff_headers(seeded, db, "partner", "9100000003")


def user_id(client, headers) -> str:
    return client.get("/api/me", headers=headers).json()["id"]


def make_student(client, phone="9200000001", dob=ADULT_DOB):
    """A student with data-processing consent (guardian consent when under 18)."""
    headers = auth_headers(register(client, phone=phone, dob=dob))
    body = GUARDIAN if dob == MINOR_DOB else {"given_by": "self"}
    assert client.post("/api/consents", json=body, headers=headers).status_code == 201
    return headers


def share_with_facilitators(client, headers, minor=False):
    body = GUARDIAN if minor else {"given_by": "self"}
    r = client.post("/api/consents/facilitator-access", json=body, headers=headers)
    assert r.status_code == 201, r.text


def assign(client, admin_headers, facilitator_headers, student_headers):
    r = client.post(
        "/api/admin/assignments",
        json={
            "facilitator_id": user_id(client, facilitator_headers),
            "student_id": user_id(client, student_headers),
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()
