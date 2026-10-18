import uuid

import pytest
from sqlalchemy import select

from app.core.audit import AuditEvent
from app.main import create_app
from app.modules.profile import service as profile_service
from app.modules.profile.models import Provenance
from app.modules.recommend.models import RecommendationRun
from tests.conftest import auth_headers, register


@pytest.fixture
def student(seeded):
    headers = auth_headers(register(seeded))
    seeded.post("/api/consents", json={"given_by": "self"}, headers=headers)
    return headers


def tell(client, headers, key, value):
    assert (
        client.put(f"/api/profile/fields/{key}", json={"value": value}, headers=headers).status_code
        == 200
    )


def recommend(client, headers, **body):
    r = client.post("/api/recommendations", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_requires_login_and_consent(seeded):
    assert seeded.post("/api/recommendations", json={}).status_code == 401
    h = auth_headers(register(seeded))
    assert seeded.post("/api/recommendations", json={}, headers=h).status_code == 403
    assert seeded.get("/api/recommendations/latest", headers=h).status_code == 403


def test_thin_profile_says_so_asks_the_right_questions_and_still_opens_doors(student, seeded):
    body = recommend(seeded, student)
    assert body["status"] == "insufficient_profile"
    assert {m["question_id"] for m in body["missing"]} == {
        "q_goals",
        "q_interests",
        "q_skills",
        "q_education_stage",
    }
    assert body["items"] and all(i["kind"] == "explore" for i in body["items"])
    assert all(i["points"] is None and i["reasons"] == [] for i in body["items"])


def test_matches_carry_reasons_prerequisites_sources_and_next_steps(student, seeded):
    tell(seeded, student, "education_stage", "class_9")
    tell(seeded, student, "interests", ["wiring", "fixing"])
    body = recommend(seeded, student, language="en")
    top = body["items"][0]
    assert (
        body["status"] == "ok" and top["kind"] == "match" and top["career"]["slug"] == "electrician"
    )
    assert top["match_level"] in {"moderate", "strong", "weak"} and top["points"] > 0
    wiring = next(r for r in top["reasons"] if r["student_term"] == "wiring")
    assert wiring["basis"] == "reported" and wiring["points"] > 0
    # Prerequisite note: informs, never excludes.
    assert top["stage"] == {
        "typical_min_stage": "class_10",
        "status": "below",
        "student_stage": "class_9",
    }
    assert {"type": "plan_prerequisite", "typical_min_stage": "class_10"} in top["next_actions"]
    # Linked platform appears with its verification and freshness.
    [src] = top["sources"]
    assert src["slug"] == "national-learning-platform" and src["freshness"] == "fresh"
    assert any(
        a["type"] == "open_route" and a["opportunity"] == "national-learning-platform"
        for a in top["next_actions"]
    )
    # Honest about what we do not know and how solid the catalog entry is.
    assert {"career_cost_unknown", "career_time_needed_unknown"} <= set(top["unknowns"])
    assert "catalog_entry_unverified" in top["flags"]
    assert "entry_requirements_are_typical_not_official" in top["flags"]
    assert "points_are_keyword_evidence_not_a_probability" in body["notes"]


def test_unknown_stage_is_flagged_and_prompts_a_question(student, seeded):
    tell(seeded, student, "interests", ["wiring"])
    top = recommend(seeded, student)["items"][0]
    assert top["stage"]["status"] == "unknown"
    assert {
        "type": "tell_us",
        "fact": "education_stage",
        "question_id": "q_education_stage",
    } in top["next_actions"]


def test_tamil_language_and_missing_translation_fallback(student, seeded):
    tell(seeded, student, "interests", ["விவசாயம்"])
    top = recommend(seeded, student, language="ta")["items"][0]
    assert top["career"]["slug"] == "dairy-farmer" and top["career"]["title"] == "பால் பண்ணையாளர்"
    assert top["language_fallback"] is False
    tell(seeded, student, "skills", ["stitching"])
    tailor = next(
        i
        for i in recommend(seeded, student, language="ta")["items"]
        if i["career"]["slug"] == "tailor"
    )
    assert tailor["career"]["title"] == "Tailor" and tailor["language_fallback"] is True


def test_goal_the_catalog_does_not_cover_is_reported_as_unmatched(student, seeded):
    tell(seeded, student, "goals", ["astronaut"])
    body = recommend(seeded, student)
    assert body["status"] == "no_matches"
    assert body["profile_summary"]["unmatched_terms"] == [{"field": "goals", "text": "astronaut"}]


def test_hypotheses_are_ignored_and_counted(student, seeded, db):
    user_id = uuid.UUID(seeded.get("/api/me", headers=student).json()["id"])
    profile_service.record_entry(
        db,
        user_id=user_id,
        key="interests",
        value=["wiring"],
        provenance=Provenance.HYPOTHESIS,
        source="system",
        recorded_by=None,
        basis="guess",
    )
    body = recommend(seeded, student)
    assert body["status"] == "insufficient_profile"
    assert body["profile_summary"]["hypotheses_ignored"] == 1


def test_observed_skills_are_used_and_count_once_when_also_reported(student, seeded, db):
    tell(seeded, student, "skills", ["wiring"])
    user_id = uuid.UUID(seeded.get("/api/me", headers=student).json()["id"])
    reported_only = recommend(seeded, student)["items"][0]["points"]
    profile_service.record_entry(
        db,
        user_id=user_id,
        key="skills",
        value=["wiring"],
        provenance=Provenance.OBSERVED,
        source="facilitator",
        recorded_by=None,
        basis="Saw wiring a board",
    )
    body = recommend(seeded, student)
    assert body["profile_summary"]["terms"] == [
        {"field": "skills", "text": "wiring", "basis": "observed"}
    ]
    assert body["items"][0]["points"] == pytest.approx(reported_only * 1.5)


def test_runs_are_stored_with_version_config_and_terms_and_latest_returns_the_newest(
    student, seeded, db
):
    tell(seeded, student, "interests", ["wiring"])
    first = recommend(seeded, student)
    tell(seeded, student, "interests", ["farming"])
    second = recommend(seeded, student)
    row = db.get(RecommendationRun, uuid.UUID(first["id"]))
    assert row.ranking_version == first["ranking_version"] and row.config["max_per_family"] == 2
    assert row.profile_summary["terms"][0]["text"] == "wiring"
    assert seeded.get("/api/recommendations/latest", headers=student).json()["id"] == second["id"]
    assert len(db.scalars(select(RecommendationRun)).all()) == 2


def test_latest_is_404_before_any_run_and_private_between_students(student, seeded):
    assert seeded.get("/api/recommendations/latest", headers=student).status_code == 404
    recommend(seeded, student)
    other = auth_headers(register(seeded, phone="9000000004"))
    seeded.post("/api/consents", json={"given_by": "self"}, headers=other)
    assert seeded.get("/api/recommendations/latest", headers=other).status_code == 404


def test_limit_validation_and_audit_keeps_counts_not_terms(student, seeded, db):
    tell(seeded, student, "interests", ["secret hobby wiring"])
    assert len(recommend(seeded, student, limit=1)["items"]) >= 1
    assert (
        seeded.post("/api/recommendations", json={"limit": 0}, headers=student).status_code == 422
    )
    assert (
        seeded.post("/api/recommendations", json={"limit": 11}, headers=student).status_code == 422
    )
    events = db.scalars(select(AuditEvent).where(AuditEvent.action == "recommendation.run")).all()
    assert all(set(e.detail) == {"status", "count"} for e in events)
    assert "secret hobby" not in str([e.detail for e in db.scalars(select(AuditEvent))])


def test_config_overrides_from_settings_change_the_ranking_and_bad_ones_fail_fast(
    settings, student, seeded
):
    from fastapi.testclient import TestClient

    tell(seeded, student, "goals", ["wiring"])
    tell(seeded, student, "interests", ["farming"])
    boosted = TestClient(
        create_app(
            settings.model_copy(update={"ranking_overrides": {"field_weights.interests": 10}})
        )
    )
    assert (
        boosted.post("/api/recommendations", json={}, headers=student).json()["items"][0]["career"][
            "slug"
        ]
        == "dairy-farmer"
    )
    default_first = seeded.post("/api/recommendations", json={}, headers=student).json()["items"][
        0
    ]["career"]["slug"]
    assert default_first == "electrician"
    with pytest.raises(ValueError, match="unknown ranking override"):
        create_app(settings.model_copy(update={"ranking_overrides": {"bogus": 1}}))
