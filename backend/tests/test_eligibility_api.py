import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.core.audit import AuditEvent
from app.modules.eligibility.models import EligibilityEvaluation
from app.modules.eligibility.service import fingerprint, rules_from_opportunity
from app.modules.profile import service as profile_service
from app.modules.profile.models import Provenance, Verification
from app.modules.sources.models import Opportunity, Publication
from tests.conftest import GUARDIAN, MINOR_DOB, auth_headers, register
from tests.fakes import FakeLLM


@pytest.fixture
def student(seeded):
    """An adult student (25) with consent, plus the headers for the seeded client."""
    headers = auth_headers(register(seeded))
    seeded.post("/api/consents", json={"given_by": "self"}, headers=headers)
    return headers


def evaluate(client, headers, slug, **extra):
    r = client.post(
        "/api/eligibility/evaluations", json={"opportunity": slug, **extra}, headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()


def tell(client, headers, key, value=None, unknown=False):
    body = {"unknown": True} if unknown else {"value": value}
    assert client.put(f"/api/profile/fields/{key}", json=body, headers=headers).status_code == 200


def test_requires_login_and_consent(seeded):
    r = seeded.post("/api/eligibility/evaluations", json={"opportunity": "fresh-scholarship"})
    assert r.status_code == 401
    h = auth_headers(register(seeded))
    r = seeded.post(
        "/api/eligibility/evaluations", json={"opportunity": "fresh-scholarship"}, headers=h
    )
    assert (r.status_code, r.json()["detail"]) == (403, "consent_required")
    assert seeded.get("/api/eligibility/evaluations", headers=h).status_code == 403


def test_unknown_when_nothing_is_told_and_it_says_what_to_ask(student, seeded):
    body = evaluate(seeded, student, "fresh-scholarship")
    assert body["outcome"] == "UNKNOWN"
    assert body["missing"] == [
        {"fact": "education_stage", "question_id": "q_education_stage"},
        {"fact": "annual_family_income_inr", "question_id": "q_annual_family_income"},
    ]
    assert body["reasons"] == ["missing_education_stage", "missing_annual_family_income_inr"]
    assert body["rules_version"] and len(body["opportunity_fingerprint"]) == 64


def test_full_journey_unknown_then_eligible_then_ineligible_then_unknown_again(student, seeded):
    tell(seeded, student, "education_stage", "class_10")
    assert evaluate(seeded, student, "fresh-scholarship")["outcome"] == "UNKNOWN"  # income missing

    tell(seeded, student, "annual_family_income_inr", 80000)
    ok = evaluate(seeded, student, "fresh-scholarship")
    assert ok["outcome"] == "ELIGIBLE" and ok["reasons"] == []
    assert ok["facts_used"]["education_stage"] == {"value": "class_10", "basis": "reported"}
    assert "based_on_self_reported_facts" in ok["flags"]

    tell(seeded, student, "annual_family_income_inr", 150000)
    no = evaluate(seeded, student, "fresh-scholarship")
    assert no["outcome"] == "INELIGIBLE" and no["reasons"] == ["family_income_above_limit"]

    # Saying "I don't know" afterwards must not leave a stale "no": it goes back to unknown.
    tell(seeded, student, "annual_family_income_inr", unknown=True)
    again = evaluate(seeded, student, "fresh-scholarship")
    assert (
        again["outcome"] == "UNKNOWN" and again["missing"][0]["fact"] == "annual_family_income_inr"
    )


def test_income_exactly_at_the_limit_is_eligible(student, seeded):
    tell(seeded, student, "education_stage", "class_9")
    tell(seeded, student, "annual_family_income_inr", 100000)
    assert evaluate(seeded, student, "fresh-scholarship")["outcome"] == "ELIGIBLE"
    tell(seeded, student, "annual_family_income_inr", 100001)
    assert evaluate(seeded, student, "fresh-scholarship")["outcome"] == "INELIGIBLE"


def test_criteria_the_engine_cannot_check_always_need_review(student, seeded):
    tell(seeded, student, "annual_family_income_inr", 100000)
    body = evaluate(seeded, student, "needs-review-scheme")
    assert body["outcome"] == "NEEDS_REVIEW" and body["reasons"] == ["other_criteria_need_review"]
    assert "has_criteria_not_checked_by_engine" in body["flags"]


def test_age_uses_the_registered_birth_date(seeded):
    adult = auth_headers(register(seeded))  # 25 years old
    minor = auth_headers(register(seeded, phone="9000000009", dob=MINOR_DOB))  # 15
    seeded.post("/api/consents", json={"given_by": "self"}, headers=adult)
    seeded.post("/api/consents", json=GUARDIAN, headers=minor)
    assert evaluate(seeded, adult, "age-limited-programme")["reasons"] == ["age_above_maximum"]
    assert evaluate(seeded, minor, "age-limited-programme")["outcome"] == "ELIGIBLE"


def test_state_restricted_record_without_verified_criteria_is_unknown_for_residents(
    student, seeded
):
    tell(seeded, student, "state", "Tamil Nadu")
    body = evaluate(seeded, student, "tamil-nadu-skilling")
    assert body["outcome"] == "UNKNOWN" and body["reasons"] == ["no_verified_criteria"]
    tell(seeded, student, "state", "Kerala")
    other = evaluate(seeded, student, "tamil-nadu-skilling")
    assert other["outcome"] == "INELIGIBLE" and other["reasons"] == ["state_not_covered"]


def test_conflicting_profile_facts_need_review(student, seeded, db):
    tell(seeded, student, "education_stage", "class_10")
    tell(seeded, student, "annual_family_income_inr", 50000)
    user_id = uuid.UUID(seeded.get("/api/me", headers=student).json()["id"])
    profile_service.record_entry(
        db,
        user_id=user_id,
        key="education_stage",
        value="class_12",
        provenance=Provenance.OBSERVED,
        source="facilitator",
        recorded_by=None,
        basis="Marksheet seen",
        verification=Verification.VERIFIED,
    )
    body = evaluate(seeded, student, "fresh-scholarship")
    assert body["outcome"] == "NEEDS_REVIEW" and body["reasons"] == ["conflicting_education_stage"]
    stage = next(c for c in body["checks"] if c["rule"] == "education_stage")
    assert stage["result"] == "conflict"


def test_a_hypothesis_is_never_used_as_a_fact(student, seeded, db):
    user_id = uuid.UUID(seeded.get("/api/me", headers=student).json()["id"])
    profile_service.record_entry(
        db,
        user_id=user_id,
        key="education_stage",
        value="class_10",
        provenance=Provenance.HYPOTHESIS,
        source="system",
        recorded_by=None,
        basis="guess",
    )
    body = evaluate(seeded, student, "fresh-scholarship")
    assert body["outcome"] == "UNKNOWN" and body["missing"][0]["fact"] == "education_stage"


def test_expired_record_is_ineligible_and_withdrawn_or_unknown_records_are_404(student, seeded, db):
    assert evaluate(seeded, student, "expired-apprenticeship")["reasons"] == ["deadline_passed"]
    r = seeded.post("/api/eligibility/evaluations", json={"opportunity": "ghost"}, headers=student)
    assert r.status_code == 404
    db.get(Opportunity, "age-limited-programme").publication_status = Publication.WITHDRAWN
    db.commit()
    r = seeded.post(
        "/api/eligibility/evaluations",
        json={"opportunity": "age-limited-programme"},
        headers=student,
    )
    assert r.status_code == 404


def test_unverified_record_never_yields_a_decision(student, seeded):
    body = evaluate(seeded, student, "unverified-welding-course")
    assert body["outcome"] == "UNKNOWN" and body["reasons"] == ["no_verified_criteria"]


def test_evaluations_are_stored_with_rule_version_facts_and_record_state(student, seeded, db):
    tell(seeded, student, "education_stage", "class_10")
    tell(seeded, student, "annual_family_income_inr", 80000)
    body = evaluate(seeded, student, "fresh-scholarship")
    row = db.get(EligibilityEvaluation, uuid.UUID(body["id"]))
    assert row.outcome == "ELIGIBLE" and row.rules_version == body["rules_version"]
    assert row.record_snapshot["verified_fields"] == [
        "url",
        "provider",
        "eligibility",
        "benefit",
        "deadline",
    ]
    assert row.record_snapshot["human_reviewed"] is False
    assert row.record_snapshot["evidence_urls"] == ["https://portal.gov.in/merit/guidelines"]
    assert row.facts_used["family_income_max"]["value"] == 80000
    assert row.evaluated_on == date.today()


def test_fingerprint_is_stable_until_the_record_changes(student, seeded, db):
    first = evaluate(seeded, student, "fresh-scholarship")["opportunity_fingerprint"]
    assert evaluate(seeded, student, "fresh-scholarship")["opportunity_fingerprint"] == first
    opp = db.get(Opportunity, "fresh-scholarship")
    assert fingerprint(rules_from_opportunity(opp)) == first
    opp.eligibility = {**opp.eligibility, "max_family_income_inr_per_year": 999}
    db.commit()
    assert evaluate(seeded, student, "fresh-scholarship")["opportunity_fingerprint"] != first


def test_history_is_newest_first_filterable_and_private(student, seeded):
    evaluate(seeded, student, "fresh-scholarship")
    evaluate(seeded, student, "age-limited-programme")
    evaluate(seeded, student, "fresh-scholarship")
    everything = seeded.get("/api/eligibility/evaluations", headers=student).json()
    assert [e["opportunity"]["slug"] for e in everything] == [
        "fresh-scholarship",
        "age-limited-programme",
        "fresh-scholarship",
    ]
    only = seeded.get(
        "/api/eligibility/evaluations?opportunity=age-limited-programme", headers=student
    ).json()
    assert len(only) == 1
    assert len(seeded.get("/api/eligibility/evaluations?limit=2", headers=student).json()) == 2

    other = auth_headers(register(seeded, phone="9000000003"))
    seeded.post("/api/consents", json={"given_by": "self"}, headers=other)
    assert seeded.get("/api/eligibility/evaluations", headers=other).json() == []


def test_audit_log_has_outcome_but_none_of_the_facts(student, seeded, db):
    tell(seeded, student, "annual_family_income_inr", 123457)
    evaluate(seeded, student, "fresh-scholarship")
    events = db.scalars(
        select(AuditEvent).where(AuditEvent.action == "eligibility.evaluated")
    ).all()
    assert [e.detail for e in events] == [
        {"opportunity": "fresh-scholarship", "outcome": "INELIGIBLE"}
    ]
    assert "123457" not in str([e.detail for e in db.scalars(select(AuditEvent))])


def test_localised_titles_and_no_llm_is_ever_involved(settings, student, seeded):
    from fastapi.testclient import TestClient

    from app.main import create_app

    llm = FakeLLM()  # any call would raise: it has no queued responses and records calls
    client = TestClient(create_app(settings, llm=llm))
    body = evaluate(client, student, "fresh-scholarship", language="ta")
    assert body["opportunity"]["title"] == "மாணவர்களுக்கான தகுதி உதவித்தொகை"
    assert llm.calls == []


def test_income_question_is_on_demand_and_collectable_through_the_profile(student, seeded):
    q = next(
        q
        for q in seeded.get("/api/interview/questions", headers=student).json()
        if q["id"] == "q_annual_family_income"
    )
    assert (q["kind"], q["min_value"], q["max_value"]) == ("number", 0, 100_000_000)
    session = seeded.post("/api/interview/sessions", headers=student).json()
    asked = []
    while session["question"]:
        asked.append(session["question"]["id"])
        r = seeded.post(
            f"/api/interview/sessions/{session['id']}/answers",
            json={"question_id": session["question"]["id"], "kind": "skip"},
            headers=student,
        )
        session = r.json()["session"]
    assert "q_annual_family_income" not in asked  # never part of the general interview
