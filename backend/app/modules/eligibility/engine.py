"""Deterministic eligibility rules engine.

Pure functions over plain data: no database, no network, no LLM. The same inputs always give
the same result, which is stored with the rule version so it can be audited and replayed.

Outcomes
  ELIGIBLE      every published criterion is modelled, checked against known facts, and met.
  INELIGIBLE    at least one criterion is definitely not met (or the deadline has passed).
  UNKNOWN       nothing failed, but a needed fact is missing, or we hold no verified criteria.
                Missing information is never treated as a "no".
  NEEDS_REVIEW  nothing failed and nothing is missing, but a person must look: the source
                states criteria the engine cannot evaluate, our facts conflict, or the record
                is stale.

Only criteria the record lists in `verified_fields` are used; anything else is ignored.
Eligibility is not suitability: nothing here says a scheme is a good idea for the student.
"""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any, Literal

RULES_VERSION = "2026-10-1"


class Outcome(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class CheckResult(StrEnum):
    PASS = "pass"  # noqa: S105 - a check result, not a password
    FAIL = "fail"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


# --- inputs ---


@dataclass(frozen=True)
class FactValue:
    value: Any
    basis: Literal["reported", "observed"]


@dataclass(frozen=True)
class Fact:
    """One student fact after combining everything we know about it."""

    status: Literal["known", "missing", "conflict"]
    value: Any = None
    basis: str | None = None  # where the value came from; "observed" wins over "reported"
    candidates: tuple[tuple[str, Any], ...] = ()  # populated for conflicts


MISSING = Fact("missing")


def resolve(values: Sequence[FactValue]) -> Fact:
    """Combine reported and observed values. Disagreement is a conflict, not a guess."""
    if not values:
        return MISSING
    distinct = {repr(v.value) for v in values}
    if len(distinct) > 1:
        return Fact("conflict", candidates=tuple((v.basis, v.value) for v in values))
    chosen = next((v for v in values if v.basis == "observed"), values[0])
    return Fact("known", chosen.value, chosen.basis)


@dataclass(frozen=True)
class StudentFacts:
    birth_date: date | None  # self-reported at registration
    education_stage: Fact = MISSING
    state: Fact = MISSING
    annual_family_income_inr: Fact = MISSING


@dataclass(frozen=True)
class OpportunityRules:
    slug: str
    eligibility: Mapping[str, Any] | None
    scope_level: str  # "national" | "state"
    scope_states: Sequence[str]
    application_deadline: date | None
    expires_on: date | None
    verified_fields: frozenset[str]
    verified_at: date | None


# --- outputs ---


@dataclass(frozen=True)
class Check:
    rule: str
    result: CheckResult
    expected: Any = None
    actual: Any = None
    basis: str | None = None  # provenance of the student fact used


@dataclass(frozen=True)
class Evaluation:
    outcome: Outcome
    reasons: list[str]
    checks: list[Check]
    missing: list[str]  # facts that would settle an UNKNOWN
    flags: list[str]
    rules_version: str
    evaluated_on: date
    facts_used: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["outcome"] = self.outcome.value
        d["checks"] = [{**c, "result": c["result"].value} for c in d["checks"]]
        d["evaluated_on"] = self.evaluated_on.isoformat()
        return d


# --- evaluation ---


def age_on(birth: date, on: date) -> int:
    return on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))


def _fact_check(rule: str, fact: Fact, expected: Any, passes: Any) -> Check:
    """Turn a (possibly missing or conflicting) fact into a check result."""
    if fact.status == "missing":
        return Check(rule, CheckResult.UNKNOWN, expected)
    if fact.status == "conflict":
        return Check(rule, CheckResult.CONFLICT, expected, [list(c) for c in fact.candidates])
    ok = passes(fact.value)
    return Check(
        rule, CheckResult.PASS if ok else CheckResult.FAIL, expected, fact.value, fact.basis
    )


_FAIL_REASON = {
    "expiry": "expired",
    "deadline": "deadline_passed",
    "state": "state_not_covered",
    "education_stage": "education_stage_not_met",
    "age_min": "age_below_minimum",
    "age_max": "age_above_maximum",
    "family_income_max": "family_income_above_limit",
}
_NEEDED_FACT = {
    "state": "state",
    "education_stage": "education_stage",
    "age_min": "date_of_birth",
    "age_max": "date_of_birth",
    "family_income_max": "annual_family_income_inr",
}


def evaluate(
    rules: OpportunityRules, facts: StudentFacts, today: date, fresh_days: int
) -> Evaluation:
    checks: list[Check] = []
    flags: list[str] = []
    verified = rules.verified_fields

    # Expiry and deadline: whether the door is still open.
    if rules.expires_on is not None:
        past = rules.expires_on < today
        checks.append(
            Check(
                "expiry",
                CheckResult.FAIL if past else CheckResult.PASS,
                rules.expires_on.isoformat(),
            )
        )
    if rules.application_deadline is not None and "deadline" in verified:
        past = rules.application_deadline < today  # the deadline day itself is still open
        checks.append(
            Check(
                "deadline",
                CheckResult.FAIL if past else CheckResult.PASS,
                rules.application_deadline.isoformat(),
            )
        )
    elif rules.application_deadline is not None:
        flags.append("deadline_not_verified")
    else:
        flags.append("deadline_unknown")

    # Geographic scope.
    if rules.scope_level == "state" and "scope" in verified:
        states = {s.casefold() for s in rules.scope_states}
        checks.append(
            _fact_check(
                "state",
                facts.state,
                sorted(rules.scope_states),
                lambda v: str(v).casefold() in states,
            )
        )

    # Published criteria (only if verified).
    elig = rules.eligibility if "eligibility" in verified else None
    criteria_unverified = rules.eligibility is not None and elig is None
    if criteria_unverified:
        flags.append("criteria_not_verified")
    modelled = False
    other_criteria: list[Any] = []
    if elig is not None:
        other_criteria = list(elig.get("other_criteria") or [])
        if (stages := elig.get("education_stages")) is not None:
            modelled = True
            checks.append(
                _fact_check("education_stage", facts.education_stage, stages, lambda v: v in stages)
            )
        age_ref = date.fromisoformat(elig["age_as_on"]) if elig.get("age_as_on") else today
        for key, rule, cmp in (
            ("min_age", "age_min", lambda age, limit: age >= limit),
            ("max_age", "age_max", lambda age, limit: age <= limit),
        ):
            limit = elig.get(key)
            if limit is None:
                continue
            modelled = True
            if facts.birth_date is None:
                checks.append(Check(rule, CheckResult.UNKNOWN, limit))
            else:
                age = age_on(facts.birth_date, age_ref)
                ok = cmp(age, limit)
                checks.append(
                    Check(
                        rule,
                        CheckResult.PASS if ok else CheckResult.FAIL,
                        {"limit": limit, "as_on": age_ref.isoformat()},
                        age,
                        "reported",
                    )
                )
        if (cap := elig.get("max_family_income_inr_per_year")) is not None:
            modelled = True  # "not more than" the cap: equal passes
            checks.append(
                _fact_check(
                    "family_income_max", facts.annual_family_income_inr, cap, lambda v: v <= cap
                )
            )

    criteria_known = elig is not None and (modelled or bool(other_criteria))
    results = {c.result for c in checks}
    reasons: list[str] = []
    missing: list[str] = []

    if CheckResult.FAIL in results:
        outcome = Outcome.INELIGIBLE
        reasons = [_FAIL_REASON[c.rule] for c in checks if c.result is CheckResult.FAIL]
    elif CheckResult.CONFLICT in results:
        outcome = Outcome.NEEDS_REVIEW
        reasons = [
            f"conflicting_{_NEEDED_FACT[c.rule]}"
            for c in checks
            if c.result is CheckResult.CONFLICT
        ]
    elif CheckResult.UNKNOWN in results:
        outcome = Outcome.UNKNOWN
        missing = list(
            dict.fromkeys(_NEEDED_FACT[c.rule] for c in checks if c.result is CheckResult.UNKNOWN)
        )
        reasons = [f"missing_{m}" for m in missing]
    elif not criteria_known:
        outcome = Outcome.UNKNOWN
        reasons = ["criteria_not_verified" if criteria_unverified else "no_verified_criteria"]
    else:
        stale = rules.verified_at is None or (today - rules.verified_at).days > fresh_days
        if other_criteria:
            reasons.append("other_criteria_need_review")
        if stale:
            reasons.append("record_stale")
        outcome = Outcome.NEEDS_REVIEW if reasons else Outcome.ELIGIBLE

    facts_used = {
        c.rule: {"value": c.actual, "basis": c.basis}
        for c in checks
        if c.basis is not None and c.result is not CheckResult.CONFLICT
    }
    reported = sorted(r for r, u in facts_used.items() if u["basis"] == "reported")
    if reported and outcome in (Outcome.ELIGIBLE, Outcome.NEEDS_REVIEW):
        flags.append("based_on_self_reported_facts")
    if other_criteria:
        flags.append("has_criteria_not_checked_by_engine")
    return Evaluation(
        outcome=outcome,
        reasons=reasons,
        checks=checks,
        missing=missing,
        flags=flags,
        rules_version=RULES_VERSION,
        evaluated_on=today,
        facts_used=facts_used,
    )
