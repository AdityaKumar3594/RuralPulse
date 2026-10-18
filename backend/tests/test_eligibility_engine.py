"""Pure engine tests: no database. Boundaries, missing data, conflicts and the 4 outcomes."""

import json
from dataclasses import replace
from datetime import date

import pytest

from app.modules.eligibility.engine import (
    MISSING,
    RULES_VERSION,
    Fact,
    FactValue,
    OpportunityRules,
    Outcome,
    StudentFacts,
    age_on,
    evaluate,
    resolve,
)

TODAY = date(2026, 10, 18)
FRESH = 180


def known(value, basis="reported"):
    return Fact("known", value, basis)


def rules(eligibility=None, **over) -> OpportunityRules:
    base = {
        "slug": "x",
        "eligibility": eligibility,
        "scope_level": "national",
        "scope_states": [],
        "application_deadline": None,
        "expires_on": None,
        "verified_fields": frozenset({"eligibility"} if eligibility is not None else set()),
        "verified_at": date(2026, 10, 1),
    }
    return OpportunityRules(**{**base, **over})


def facts(**over) -> StudentFacts:
    return StudentFacts(**{"birth_date": date(2010, 6, 15), **over})


def run(r, f, today=TODAY):
    return evaluate(r, f, today, FRESH)


# --- the four outcomes ---


def test_eligible_when_every_modelled_criterion_is_known_and_met():
    r = rules({"education_stages": ["class_10"], "max_family_income_inr_per_year": 350000})
    ev = run(r, facts(education_stage=known("class_10"), annual_family_income_inr=known(200000)))
    assert ev.outcome is Outcome.ELIGIBLE and ev.reasons == [] and ev.missing == []
    assert ev.rules_version == RULES_VERSION and ev.evaluated_on == TODAY
    assert {c.rule for c in ev.checks} == {"education_stage", "family_income_max"}


def test_ineligible_when_a_criterion_definitely_fails():
    r = rules({"education_stages": ["class_9", "class_10"]})
    ev = run(r, facts(education_stage=known("graduate")))
    assert ev.outcome is Outcome.INELIGIBLE and ev.reasons == ["education_stage_not_met"]
    assert ev.missing == []  # no point asking for more once it has failed


def test_unknown_when_a_needed_fact_is_missing_and_never_ineligible():
    r = rules({"education_stages": ["class_10"], "max_family_income_inr_per_year": 350000})
    ev = run(r, facts(education_stage=known("class_10")))  # income not told
    assert ev.outcome is Outcome.UNKNOWN
    assert ev.missing == ["annual_family_income_inr"] and ev.reasons == [
        "missing_annual_family_income_inr"
    ]


def test_needs_review_when_the_source_has_criteria_the_engine_cannot_check():
    r = rules(
        {"max_family_income_inr_per_year": 350000, "other_criteria": [{"en": "Government school"}]}
    )
    ev = run(r, facts(annual_family_income_inr=known(100000)))
    assert ev.outcome is Outcome.NEEDS_REVIEW and ev.reasons == ["other_criteria_need_review"]
    assert "has_criteria_not_checked_by_engine" in ev.flags


def test_a_failed_modelled_rule_beats_unchecked_criteria():
    r = rules({"max_family_income_inr_per_year": 100, "other_criteria": [{"en": "x"}]})
    assert run(r, facts(annual_family_income_inr=known(500))).outcome is Outcome.INELIGIBLE


# --- missing is not negative ---


def test_everything_missing_is_unknown_with_all_missing_facts_listed():
    r = rules(
        {
            "education_stages": ["class_10"],
            "min_age": 14,
            "max_family_income_inr_per_year": 1,
        },
        scope_level="state",
        scope_states=["Tamil Nadu"],
        verified_fields=frozenset({"eligibility", "scope"}),
    )
    ev = run(r, StudentFacts(birth_date=None))
    assert ev.outcome is Outcome.UNKNOWN
    assert ev.missing == ["state", "education_stage", "date_of_birth", "annual_family_income_inr"]


def test_no_verified_criteria_is_unknown_not_eligible():
    assert run(rules(None), facts()).reasons == ["no_verified_criteria"]
    assert run(rules(None), facts()).outcome is Outcome.UNKNOWN


def test_unverified_criteria_are_ignored_entirely():
    # Eligibility is present on the record but NOT listed as verified: it must not be applied,
    # so an apparent mismatch cannot turn into INELIGIBLE.
    r = rules({"education_stages": ["class_9"]}, verified_fields=frozenset())
    ev = run(r, facts(education_stage=known("graduate")))
    assert ev.outcome is Outcome.UNKNOWN and ev.reasons == ["criteria_not_verified"]
    assert ev.checks == [] and "criteria_not_verified" in ev.flags


def test_verified_but_empty_eligibility_is_unknown():
    assert run(rules({}), facts()).reasons == ["no_verified_criteria"]


# --- boundaries ---


@pytest.mark.parametrize(
    ("birth", "min_age", "max_age", "expected"),
    [
        (date(2012, 10, 18), 14, None, Outcome.ELIGIBLE),  # turns 14 today: meets the minimum
        (date(2012, 10, 19), 14, None, Outcome.INELIGIBLE),  # turns 14 tomorrow
        (date(2000, 10, 18), None, 26, Outcome.ELIGIBLE),  # 26 today: at the maximum
        (date(2000, 10, 17), None, 25, Outcome.INELIGIBLE),  # 26 yesterday, max 25
        (date(2000, 10, 19), None, 25, Outcome.ELIGIBLE),  # still 25 until tomorrow
        (date(2008, 2, 29), 18, None, Outcome.ELIGIBLE),  # leap-day birthday, long past 18
    ],
)
def test_age_boundaries_are_inclusive_and_exact(birth, min_age, max_age, expected):
    elig = {k: v for k, v in {"min_age": min_age, "max_age": max_age}.items() if v is not None}
    assert run(rules(elig), StudentFacts(birth_date=birth)).outcome is expected


def test_age_is_measured_on_the_stated_reference_date():
    elig = {"max_age": 18, "age_as_on": "2026-07-01"}
    born = StudentFacts(birth_date=date(2008, 8, 1))  # 17 on 1 July, 18 by October
    assert run(rules(elig), born).outcome is Outcome.ELIGIBLE
    assert run(rules({"max_age": 17}), born).outcome is Outcome.INELIGIBLE  # measured today: 18


def test_age_on_helper():
    assert age_on(date(2010, 2, 28), date(2026, 2, 27)) == 15
    assert age_on(date(2010, 2, 28), date(2026, 2, 28)) == 16


@pytest.mark.parametrize(
    ("income", "expected"),
    [
        (349999, Outcome.ELIGIBLE),
        (350000, Outcome.ELIGIBLE),
        (350001, Outcome.INELIGIBLE),
        (0, Outcome.ELIGIBLE),
    ],
)
def test_income_cap_is_not_more_than(income, expected):
    r = rules({"max_family_income_inr_per_year": 350000})
    assert run(r, facts(annual_family_income_inr=known(income))).outcome is expected


def test_deadline_day_itself_is_open_and_the_day_after_is_not():
    r = rules(
        {"education_stages": ["class_10"]},
        application_deadline=date(2026, 10, 18),
        verified_fields=frozenset({"eligibility", "deadline"}),
    )
    f = facts(education_stage=known("class_10"))
    assert run(r, f, today=date(2026, 10, 18)).outcome is Outcome.ELIGIBLE
    late = run(r, f, today=date(2026, 10, 19))
    assert late.outcome is Outcome.INELIGIBLE and late.reasons == ["deadline_passed"]


def test_unverified_deadline_is_flagged_not_enforced_and_missing_deadline_is_flagged():
    r = rules({"education_stages": ["class_10"]}, application_deadline=date(2020, 1, 1))
    ev = run(r, facts(education_stage=known("class_10")))
    assert ev.outcome is Outcome.ELIGIBLE and "deadline_not_verified" in ev.flags
    assert (
        "deadline_unknown"
        in run(
            rules({"education_stages": ["class_10"]}), facts(education_stage=known("class_10"))
        ).flags
    )


def test_expiry_blocks_even_without_verified_criteria():
    ev = run(rules(None, expires_on=date(2026, 10, 17)), facts())
    assert ev.outcome is Outcome.INELIGIBLE and ev.reasons == ["expired"]
    assert run(rules(None, expires_on=date(2026, 10, 18)), facts()).outcome is Outcome.UNKNOWN


def test_state_scope_is_case_insensitive_and_restricts_only_when_verified():
    r = rules(
        None, scope_level="state", scope_states=["Tamil Nadu"], verified_fields=frozenset({"scope"})
    )
    assert (
        run(r, facts(state=known("tamil nadu"))).outcome is Outcome.UNKNOWN
    )  # in scope, but criteria unknown
    out = run(r, facts(state=known("Kerala")))
    assert out.outcome is Outcome.INELIGIBLE and out.reasons == ["state_not_covered"]
    unverified = replace(r, verified_fields=frozenset())
    assert all(c.rule != "state" for c in run(unverified, facts(state=known("Kerala"))).checks)


def test_state_scope_with_known_criteria_can_be_eligible():
    r = rules(
        {"education_stages": ["class_10"]},
        scope_level="state",
        scope_states=["Tamil Nadu"],
        verified_fields=frozenset({"eligibility", "scope"}),
    )
    ok = run(r, facts(education_stage=known("class_10"), state=known("Tamil Nadu")))
    assert ok.outcome is Outcome.ELIGIBLE


def test_stale_record_with_passing_facts_needs_review():
    r = rules({"education_stages": ["class_10"]}, verified_at=date(2026, 10, 18))
    f = facts(education_stage=known("class_10"))
    assert run(r, f, today=date(2027, 4, 16)).outcome is Outcome.ELIGIBLE  # day 180
    stale = run(r, f, today=date(2027, 4, 17))  # day 181
    assert stale.outcome is Outcome.NEEDS_REVIEW and stale.reasons == ["record_stale"]
    never = run(replace(r, verified_at=None), f)
    assert never.reasons == ["record_stale"]


# --- conflicts and provenance ---


def test_resolve_agreement_conflict_and_precedence():
    assert resolve([]) is MISSING
    both = resolve([FactValue("class_10", "reported"), FactValue("class_10", "observed")])
    assert both.status == "known" and both.basis == "observed"
    clash = resolve([FactValue("class_10", "reported"), FactValue("class_9", "observed")])
    assert clash.status == "conflict" and set(clash.candidates) == {
        ("reported", "class_10"),
        ("observed", "class_9"),
    }


def test_conflicting_facts_need_review_instead_of_a_guess():
    r = rules({"education_stages": ["class_10"]})
    conflict = resolve([FactValue("class_10", "reported"), FactValue("class_9", "observed")])
    ev = run(r, facts(education_stage=conflict))
    assert ev.outcome is Outcome.NEEDS_REVIEW and ev.reasons == ["conflicting_education_stage"]


def test_a_definite_failure_still_wins_over_a_conflict_elsewhere():
    r = rules({"education_stages": ["class_10"], "max_family_income_inr_per_year": 10})
    conflict = resolve([FactValue("class_10", "reported"), FactValue("class_9", "observed")])
    ev = run(r, facts(education_stage=conflict, annual_family_income_inr=known(999)))
    assert ev.outcome is Outcome.INELIGIBLE


def test_self_reported_basis_is_recorded_and_flagged():
    r = rules({"education_stages": ["class_10"]})
    reported = run(r, facts(education_stage=known("class_10", "reported")))
    assert reported.facts_used["education_stage"] == {"value": "class_10", "basis": "reported"}
    assert "based_on_self_reported_facts" in reported.flags
    observed = run(r, facts(education_stage=known("class_10", "observed")))
    assert "based_on_self_reported_facts" not in observed.flags


# --- properties ---


def test_evaluation_is_deterministic_serialisable_and_does_not_mutate_inputs():
    r = rules({"education_stages": ["class_10"], "max_family_income_inr_per_year": 350000})
    f = facts(education_stage=known("class_10"), annual_family_income_inr=known(1))
    first, second = run(r, f), run(r, f)
    assert first == second
    assert json.loads(json.dumps(first.to_dict()))["outcome"] == "ELIGIBLE"
    assert r.eligibility == {
        "education_stages": ["class_10"],
        "max_family_income_inr_per_year": 350000,
    }


def test_outcome_names_are_exactly_the_four_documented_states():
    assert {o.value for o in Outcome} == {"ELIGIBLE", "INELIGIBLE", "UNKNOWN", "NEEDS_REVIEW"}


def test_eligibility_package_never_imports_the_ai_layer():
    # The LLM must never make or influence the decision: enforce it structurally.
    from pathlib import Path

    package = Path(__file__).resolve().parents[1] / "app" / "modules" / "eligibility"
    for path in package.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "app.ai" not in text and "anthropic" not in text, path.name
