import pytest
from sqlalchemy import select

from app.main import create_app
from app.modules.interview.models import InterviewAnswer
from app.modules.interview.questions import QUESTIONS
from app.modules.profile.models import ProfileEntry
from tests.conftest import GUARDIAN, MINOR_DOB, auth_headers, register
from tests.fakes import FakeLLM


def start(client, headers, **body):
    r = client.post("/api/interview/sessions", json=body or None, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def answer(client, headers, session, question_id, kind="value", **kw):
    return client.post(
        f"/api/interview/sessions/{session['id']}/answers",
        json={"question_id": question_id, "kind": kind, **kw},
        headers=headers,
    )


def profile_field(client, headers, key):
    fields = client.get("/api/profile", headers=headers).json()["fields"]
    return next(f for f in fields if f["key"] == key)


def test_requires_login_and_consent(client_with_db):
    assert client_with_db.post("/api/interview/sessions").status_code == 401
    h = auth_headers(register(client_with_db))
    r = client_with_db.post("/api/interview/sessions", headers=h)
    assert (r.status_code, r.json()["detail"]) == (403, "consent_required")


def test_minor_needs_guardian_consent_first(client_with_db):
    h = auth_headers(register(client_with_db, dob=MINOR_DOB))
    assert client_with_db.post("/api/interview/sessions", headers=h).status_code == 403
    client_with_db.post("/api/consents", json=GUARDIAN, headers=h)
    assert client_with_db.post("/api/interview/sessions", headers=h).status_code == 200


def test_start_returns_first_question_in_requested_language(client_with_db, adult):
    s = start(client_with_db, adult, language="ta")
    assert s["status"] == "active" and s["language"] == "ta"
    q = s["question"]
    assert q["id"] == "q_education_stage" and q["kind"] == "single_choice"
    assert q["prompt"].startswith("நீங்கள்")
    assert {o["value"] for o in q["options"]} >= {"class_10", "not_in_school"}


def test_default_language_comes_from_the_student(client_with_db):
    h = auth_headers(register(client_with_db, preferred_language="en"))
    client_with_db.post("/api/consents", json={"given_by": "self"}, headers=h)
    assert start(client_with_db, h)["language"] == "en"


def test_resume_returns_same_session_and_next_unanswered_question(client_with_db, adult):
    s = start(client_with_db, adult)
    answer(client_with_db, adult, s, "q_education_stage", value="class_10")
    resumed = start(client_with_db, adult)
    assert resumed["id"] == s["id"]
    assert resumed["question"]["id"] == "q_interests"
    current = client_with_db.get("/api/interview/sessions/current", headers=adult).json()
    assert current["id"] == s["id"]


def test_no_current_session_is_404(client_with_db, adult):
    assert client_with_db.get("/api/interview/sessions/current", headers=adult).status_code == 404


def test_structured_answer_updates_profile_with_provenance_and_advances(client_with_db, adult):
    s = start(client_with_db, adult)
    r = answer(client_with_db, adult, s, "q_education_stage", value="class_10")
    body = r.json()
    assert (body["outcome"], body["interpreted_by"], body["corrected"]) == (
        "recorded",
        "student",
        False,
    )
    assert body["session"]["question"]["id"] == "q_interests"
    assert body["session"]["progress"]["answered"] == 1
    [entry] = profile_field(client_with_db, adult, "education_stage")["entries"]
    assert (entry["provenance"], entry["value"], entry["source"]) == (
        "reported",
        "class_10",
        "interview:q_education_stage",
    )


def test_invalid_structured_answer_is_rejected_and_changes_nothing(client_with_db, adult):
    s = start(client_with_db, adult)
    assert answer(client_with_db, adult, s, "q_education_stage", value="phd").status_code == 422
    assert profile_field(client_with_db, adult, "education_stage")["entries"] == []
    assert answer(client_with_db, adult, s, "q_nope", value="x").status_code == 404


def test_request_shape_is_validated(client_with_db, adult):
    s = start(client_with_db, adult)
    for body in (
        {"question_id": "q_goals", "kind": "value"},
        {"question_id": "q_goals", "kind": "text", "text": "  "},
        {"question_id": "q_goals", "kind": "skip", "text": "x"},
        {"question_id": "q_goals", "kind": "text", "text": "x" * 501},
    ):
        r = client_with_db.post(
            f"/api/interview/sessions/{s['id']}/answers", json=body, headers=adult
        )
        assert r.status_code == 422, body


def test_unknown_answer_is_stored_as_unknown_and_not_asked_again(client_with_db, adult):
    s = start(client_with_db, adult)
    r = answer(client_with_db, adult, s, "q_education_stage", kind="unknown").json()
    assert r["outcome"] == "unknown"
    assert r["session"]["question"]["id"] != "q_education_stage"
    f = profile_field(client_with_db, adult, "education_stage")
    assert f["state"] == "unknown" and f["entries"][0]["provenance"] == "unknown"


def test_skip_leaves_profile_untouched_and_moves_on_but_returns_next_session(client_with_db, adult):
    s = start(client_with_db, adult)
    r = answer(client_with_db, adult, s, "q_education_stage", kind="skip").json()
    assert r["outcome"] == "skipped"
    assert r["session"]["question"]["id"] == "q_interests"
    assert profile_field(client_with_db, adult, "education_stage")["entries"] == []
    # Skipped in this session, but a later session asks again.
    for q in QUESTIONS:
        answer(client_with_db, adult, s, q.id, kind="skip")
    assert client_with_db.get("/api/interview/sessions/current", headers=adult).status_code == 404
    assert start(client_with_db, adult)["question"]["id"] == "q_education_stage"


def test_correction_replaces_the_value_and_is_flagged(client_with_db, adult):
    s = start(client_with_db, adult)
    answer(client_with_db, adult, s, "q_education_stage", value="class_10")
    r = answer(client_with_db, adult, s, "q_education_stage", value="class_11").json()
    assert r["corrected"] is True
    [entry] = profile_field(client_with_db, adult, "education_stage")["entries"]
    assert entry["value"] == "class_11"
    # ...and the next question is unchanged by the correction.
    assert r["session"]["question"]["id"] == "q_interests"


def test_not_in_school_skips_school_questions(client_with_db, adult):
    s = start(client_with_db, adult)
    s = answer(client_with_db, adult, s, "q_education_stage", value="not_in_school").json()[
        "session"
    ]
    seen = []
    while s["question"]:
        seen.append(s["question"]["id"])
        s = answer(client_with_db, adult, s, s["question"]["id"], kind="unknown").json()["session"]
    assert "q_subject_preferences" not in seen and "q_subjects_studied" not in seen
    assert seen[0] == "q_interests"


def test_completing_the_interview_closes_the_session(client_with_db, adult):
    s = start(client_with_db, adult)
    last = None
    while s["question"]:
        last = answer(client_with_db, adult, s, s["question"]["id"], kind="unknown").json()
        s = last["session"]
    assert s["status"] == "completed" and s["progress"]["answered"] == s["progress"]["total"]
    assert answer(client_with_db, adult, s, "q_goals", kind="unknown").status_code == 409
    # Nothing left to ask: a new session completes immediately instead of looping.
    assert start(client_with_db, adult)["status"] == "completed"


def test_students_cannot_touch_each_others_sessions(client_with_db, adult):
    s = start(client_with_db, adult)
    other = auth_headers(register(client_with_db, phone="9000000002"))
    client_with_db.post("/api/consents", json={"given_by": "self"}, headers=other)
    r = answer(client_with_db, other, s, "q_education_stage", value="class_10")
    assert r.status_code == 404
    assert profile_field(client_with_db, adult, "education_stage")["entries"] == []


def test_answer_cap_per_session(client_with_db, adult, monkeypatch):
    from app.modules.interview import service

    monkeypatch.setattr(service, "MAX_ANSWERS_PER_SESSION", 2)
    s = start(client_with_db, adult)
    assert (
        answer(client_with_db, adult, s, "q_education_stage", value="class_10").status_code == 200
    )
    assert (
        answer(client_with_db, adult, s, "q_education_stage", value="class_11").status_code == 200
    )
    assert (
        answer(client_with_db, adult, s, "q_education_stage", value="class_12").status_code == 429
    )


# --- free text and AI ---


@pytest.fixture
def with_llm(settings, client_with_db):
    """Same database and test client, but with a fake LLM wired in."""
    from fastapi.testclient import TestClient

    def build(*responses):
        llm = FakeLLM(*responses)
        return TestClient(create_app(settings, llm=llm)), llm

    return build


def test_free_text_choice_is_interpreted_by_ai_and_marked_as_such(with_llm, adult, client_with_db):
    client, llm = with_llm({"match": "class_10", "confidence": "high", "quote": "tenth"})
    s = start(client, adult)
    r = answer(client, adult, s, "q_education_stage", kind="text", text="I study in tenth")
    body = r.json()
    assert (body["outcome"], body["interpreted_by"]) == ("recorded", "ai")
    [entry] = profile_field(client, adult, "education_stage")["entries"]
    assert entry["source"] == "interview:q_education_stage:ai"
    assert len(llm.calls) == 1


def test_ambiguous_text_asks_again_then_moves_on(with_llm, adult):
    unclear = {"match": "unclear", "confidence": "low", "quote": ""}
    client, _ = with_llm(unclear, unclear)
    s = start(client, adult, language="en")
    first = answer(
        client, adult, s, "q_education_stage", kind="text", text="hmm maybe a bit of both"
    ).json()
    assert first["outcome"] == "needs_clarification"
    assert first["session"]["question"]["id"] == "q_education_stage"  # same question again
    assert "choose" in first["message"].lower()
    second = answer(
        client, adult, s, "q_education_stage", kind="text", text="not sure what to say"
    ).json()
    assert second["outcome"] == "skipped"
    assert second["session"]["question"]["id"] == "q_interests"
    assert profile_field(client, adult, "education_stage")["entries"] == []


def test_clarification_message_is_localised(with_llm, adult):
    client, _ = with_llm({"match": "unclear", "confidence": "low", "quote": ""})
    s = start(client, adult, language="ta")
    r = answer(
        client, adult, s, "q_education_stage", kind="text", text="தெரியவில்லை ஏதோ ஒன்று"
    ).json()
    assert r["message"].startswith("நீங்கள்")


def test_free_text_list_without_llm_uses_deterministic_split(client_with_db, adult):
    s = start(client_with_db, adult)
    answer(client_with_db, adult, s, "q_education_stage", value="class_10")
    r = answer(client_with_db, adult, s, "q_interests", kind="text", text="farming, drawing").json()
    assert (r["outcome"], r["interpreted_by"]) == ("recorded", "deterministic")
    [entry] = profile_field(client_with_db, adult, "interests")["entries"]
    assert entry["value"] == ["farming", "drawing"]
    assert entry["source"] == "interview:q_interests"  # no ":ai" suffix


def test_choice_text_without_llm_asks_to_choose(client_with_db, adult):
    s = start(client_with_db, adult)
    r = answer(client_with_db, adult, s, "q_education_stage", kind="text", text="tenth").json()
    assert r["outcome"] == "needs_clarification"
    assert profile_field(client_with_db, adult, "education_stage")["entries"] == []


def test_ai_outage_still_lets_students_answer_lists(with_llm, adult):
    from app.ai.base import LLMUnavailable

    client, _ = with_llm(LLMUnavailable("APIConnectionError"))
    s = start(client, adult)
    text = "I like fixing bikes and painting walls at home"
    r = answer(client, adult, s, "q_interests", kind="text", text=text).json()
    assert (r["outcome"], r["interpreted_by"]) == ("recorded", "deterministic")


def test_answer_rows_keep_raw_text_only_for_free_text(client_with_db, adult, db):
    s = start(client_with_db, adult)
    answer(client_with_db, adult, s, "q_education_stage", value="class_10")
    answer(client_with_db, adult, s, "q_interests", kind="text", text="farming, drawing")
    rows = {r.question_id: r for r in db.scalars(select(InterviewAnswer))}
    assert rows["q_education_stage"].raw_text is None
    assert rows["q_interests"].raw_text == "farming, drawing"


def test_interview_only_writes_reported_or_unknown_entries(client_with_db, adult, db):
    s = start(client_with_db, adult)
    while s["question"]:
        s = answer(client_with_db, adult, s, s["question"]["id"], kind="unknown").json()["session"]
    assert {e.provenance.value for e in db.scalars(select(ProfileEntry))} == {"unknown"}


def test_question_list_is_localised_and_complete(client_with_db, adult):
    ta = client_with_db.get("/api/interview/questions?language=ta", headers=adult).json()
    en = client_with_db.get("/api/interview/questions?language=en", headers=adult).json()
    assert [q["id"] for q in ta] == [q.id for q in QUESTIONS] == [q["id"] for q in en]
    assert ta[0]["prompt"] != en[0]["prompt"]
    assert (
        client_with_db.get("/api/interview/questions?language=fr", headers=adult).status_code == 422
    )
    assert client_with_db.get("/api/interview/questions").status_code == 401
