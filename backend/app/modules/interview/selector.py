"""Pure next-question selection: no database, no AI. Easy to test and to explain."""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.modules.interview.questions import Question


@dataclass(frozen=True)
class ProfileSnapshot:
    answered: frozenset[
        str
    ]  # fields with a student statement (value or "unknown") or an observation
    values: Mapping[str, Any]  # known values, used by `applies_when` conditions


def applicable(question: Question, snapshot: ProfileSnapshot) -> bool:
    if question.on_demand:
        return False  # asked only when something (e.g. an eligibility check) needs it
    return question.applies_when is None or question.applies_when(snapshot.values)


def next_question(
    bank: Sequence[Question], snapshot: ProfileSnapshot, skipped: Collection[str]
) -> Question | None:
    """Highest-priority applicable question that is neither answered nor skipped.

    Ties keep bank order. An "unknown" answer counts as answered: we don't nag.
    """
    candidates = [
        q
        for q in bank
        if q.field_key not in snapshot.answered and q.id not in skipped and applicable(q, snapshot)
    ]
    return max(candidates, key=lambda q: q.priority, default=None)  # max returns the first of ties


def progress(bank: Sequence[Question], snapshot: ProfileSnapshot) -> tuple[int, int]:
    """(answered, total) over the questions that currently apply."""
    relevant = [q for q in bank if applicable(q, snapshot)]
    return sum(q.field_key in snapshot.answered for q in relevant), len(relevant)
