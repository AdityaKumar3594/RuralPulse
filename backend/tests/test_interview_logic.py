from app.modules.interview.questions import BY_ID, FALLBACK_LANG, QUESTIONS, localize
from app.modules.interview.selector import ProfileSnapshot, next_question, progress
from app.modules.profile.fields import FIELDS


def snap(answered=(), **values):
    return ProfileSnapshot(frozenset(answered), values)


# --- question bank ---


def test_ids_are_unique_and_prefixed():
    ids = [q.id for q in QUESTIONS]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("q_") for i in ids)


def test_every_question_targets_a_real_field_and_has_both_languages():
    for q in QUESTIONS:
        assert q.field_key in FIELDS
        for text in (q.prompt, q.why, *(o.label for o in q.options)):
            assert text.get("en") and text.get("ta"), q.id


def test_choice_options_are_valid_values_for_the_field():
    for q in QUESTIONS:
        assert (q.kind == "single_choice") == bool(q.options), q.id
        for option in q.options:
            FIELDS[q.field_key].validate(option.value)


def test_unsupported_language_falls_back_to_english():
    q = BY_ID["q_interests"]
    assert localize(q.prompt, "hi") == q.prompt[FALLBACK_LANG]
    assert localize(q.prompt, "ta") == q.prompt["ta"]


def test_no_question_requires_knowing_career_names():
    goals = BY_ID["q_goals"]
    assert "do not know" in goals.prompt["en"].lower() or "not know" in goals.why["en"].lower()


# --- selector ---


def test_starts_with_highest_priority_question():
    assert next_question(QUESTIONS, snap(), set()).id == "q_education_stage"


def test_answered_fields_are_not_asked_again():
    q = next_question(
        QUESTIONS, snap(answered={"education_stage"}, education_stage="class_10"), set()
    )
    assert q.id == "q_interests"


def test_unknown_answer_counts_as_answered_so_we_do_not_nag():
    q = next_question(QUESTIONS, snap(answered={"education_stage"}), set())
    assert q.field_key != "education_stage"


def test_skipped_questions_are_not_asked_in_this_session():
    q = next_question(QUESTIONS, snap(), {"q_education_stage"})
    assert q.id == "q_interests"


def test_conditional_questions_follow_the_education_stage():
    school = snap(answered={"education_stage"}, education_stage="class_10")
    out = snap(answered={"education_stage"}, education_stage="not_in_school")
    ids = lambda s: {q.id for q in QUESTIONS if q.applies_when is None or q.applies_when(s.values)}  # noqa: E731
    assert {"q_subject_preferences", "q_subjects_studied"} <= ids(school)
    assert not {"q_subject_preferences", "q_subjects_studied"} & ids(out)


def test_subjects_studied_waits_until_stage_is_known():
    ids = {q.id for q in QUESTIONS if q.applies_when is None or q.applies_when({})}
    assert "q_subjects_studied" not in ids


def test_returns_none_when_everything_is_answered_or_skipped():
    everything = {q.field_key for q in QUESTIONS}
    assert next_question(QUESTIONS, snap(answered=everything), set()) is None
    assert next_question(QUESTIONS, snap(), {q.id for q in QUESTIONS}) is None


def test_progress_counts_only_applicable_questions():
    answered, total = progress(
        QUESTIONS, snap(answered={"education_stage"}, education_stage="not_in_school")
    )
    assert answered == 1
    general = [q for q in QUESTIONS if not q.on_demand]
    assert total == len(general) - 2  # two school-related questions do not apply


def test_on_demand_questions_never_appear_in_the_general_flow():
    on_demand = [q for q in QUESTIONS if q.on_demand]
    assert [q.id for q in on_demand] == ["q_annual_family_income"]
    everything_else = {q.field_key for q in QUESTIONS if not q.on_demand}
    chosen = next_question(QUESTIONS, snap(answered=everything_else), set())
    assert chosen is None  # the income question is not offered even when nothing else is left
    assert on_demand[0].allow_ai is False  # eligibility inputs are never LLM-converted
