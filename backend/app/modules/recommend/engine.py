"""Explainable, configurable career ranking. Pure code: no database, no network, no LLM.

How it works
- The student's own words (goals, interests, skills, liked subjects) are broken into terms.
- Each term is matched against a career's keywords, title, skills, activities and description.
  A match earns points = (weight of the student's field) x (weight of the career field it hit)
  x (match strength). Every point is recorded as a reason, so the total can be explained.
- Observed skills (seen by a teacher) count more than reported ones. Hypotheses are ignored:
  an unconfirmed guess never drives a recommendation.
- Results are capped per career family and padded with a few "explore" careers from families the
  student did not mention, so the list widens options instead of narrowing them.

What the numbers are NOT
- `points` is keyword-match evidence, not a probability of success or a measure of ability.
  Interest is not ability, and missing evidence is not inability. The education stage never
  removes a career; it only produces a prerequisite note (and a small configurable bonus for
  careers reachable now).
- We hold no cost, duration or location data per career, so those are reported as unknown.
"""

import hashlib
import math
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Literal

RANKING_VERSION = "2026-10-1"

# Approximate order of education stages, used only for prerequisite notes.
STAGE_RANK = {
    "class_9": 9,
    "class_10": 10,
    "iti_or_diploma": 11,
    "class_11": 11,
    "class_12": 12,
    "undergraduate": 13,
    "graduate": 14,
}

CAREER_FIELDS = ("keywords", "title", "skills", "activities", "description")


@dataclass(frozen=True)
class RankingConfig:
    # How much each kind of student statement counts.
    field_weights: dict[str, float] = field(
        default_factory=lambda: {
            "goals": 3.0,
            "interests": 2.0,
            "skills": 2.0,
            "subject_preferences": 1.0,
        }
    )
    # How much a hit in each part of the career record counts.
    career_field_weights: dict[str, float] = field(
        default_factory=lambda: {
            "keywords": 1.0,
            "title": 1.0,
            "skills": 0.8,
            "activities": 0.6,
            "description": 0.3,
        }
    )
    observed_multiplier: float = 1.5
    stage_bonus: float = 0.5  # only added to careers that already matched
    strong_at: float = 4.0
    moderate_at: float = 2.0
    max_per_family: int = 2
    explore_count: int = 2
    max_terms_per_field: int = 10
    # Words that appear in many careers say little; their weight never drops below this.
    min_word_weight: float = 0.15

    @classmethod
    def from_overrides(cls, overrides: dict[str, float] | None) -> "RankingConfig":
        """Apply flat overrides like {"field_weights.goals": 4, "stage_bonus": 0}."""
        config = cls()
        for key, value in (overrides or {}).items():
            if value < 0:
                raise ValueError(f"ranking override {key} must not be negative")
            group, _, name = key.partition(".")
            if name and group in ("field_weights", "career_field_weights"):
                weights = dict(getattr(config, group))
                if name not in weights:
                    raise ValueError(f"unknown ranking override {key}")
                weights[name] = float(value)
                config = replace(config, **{group: weights})
            elif not name and key in ("max_per_family", "explore_count", "max_terms_per_field"):
                config = replace(config, **{key: int(value)})
            elif not name and key in (
                "observed_multiplier",
                "stage_bonus",
                "strong_at",
                "moderate_at",
                "min_word_weight",
            ):
                config = replace(config, **{key: float(value)})
            else:
                raise ValueError(f"unknown ranking override {key}")
        if config.max_per_family < 1:
            raise ValueError("max_per_family must be at least 1")
        return config


# --- inputs ---


@dataclass(frozen=True)
class ProfileTerm:
    field: str  # goals | interests | skills | subject_preferences
    text: str
    tokens: tuple[str, ...]
    basis: Literal["reported", "observed"]


@dataclass(frozen=True)
class StudentView:
    terms: tuple[ProfileTerm, ...]
    stage: str | None = None  # education_stage, if known
    seed: str = ""  # makes the "explore" picks reproducible per student


@dataclass(frozen=True)
class CareerDoc:
    slug: str
    family: str
    # career field -> ((original text, tokens), ...)
    fields: dict[str, tuple[tuple[str, tuple[str, ...]], ...]]
    min_stage: str | None = None


# --- outputs ---


@dataclass(frozen=True)
class Reason:
    student_field: str
    student_term: str
    basis: str
    career_field: str
    matched_text: str
    points: float


@dataclass(frozen=True)
class Recommendation:
    slug: str
    family: str
    kind: Literal["match", "explore"]
    points: float | None  # keyword-match points; None for explore picks. Not a probability.
    match_level: Literal["strong", "moderate", "weak"] | None
    reasons: list[Reason]
    stage: dict[str, Any]
    unknowns: list[str]


@dataclass(frozen=True)
class RankResult:
    status: Literal["ok", "no_matches", "insufficient_profile"]
    recommendations: list[Recommendation]
    families: list[str]
    # Student statements that matched no career at all: the catalog may simply lack them.
    unmatched_terms: list[dict[str, str]] = field(default_factory=list)
    ranking_version: str = RANKING_VERSION
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- matching ---

MIN_PREFIX = 4  # a shared stem shorter than this (in characters) is too weak to count


def token_match(a: str, b: str) -> float:
    """1.0 for the same word; 0.7 when the shorter is a stem of the longer (>= 4 chars)."""
    if a == b:
        return 1.0
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) >= MIN_PREFIX and long_.startswith(short):
        return 0.7
    return 0.0


def word_weights(careers: list[CareerDoc], floor: float) -> dict[str, float]:
    """Rarer words weigh more: 'using' appears in many careers, 'tractor' in few.

    weight = ln((N+1)/(df+1)) / ln(N+1), never below `floor`. Words absent from the catalog get 1.
    """
    n = len(careers)
    df: dict[str, int] = {}
    for career in careers:
        seen = {
            tok for entries in career.fields.values() for _, tokens in entries for tok in tokens
        }
        for tok in seen:
            df[tok] = df.get(tok, 0) + 1
    if n == 0:
        return {}
    return {
        tok: max(floor, math.log((n + 1) / (count + 1)) / math.log(n + 1))
        for tok, count in df.items()
    }


def _phrase_match(
    term: tuple[str, ...], element: tuple[str, ...], weights: dict[str, float]
) -> float:
    """Strength of matching a student's term against one career phrase, 0 to 1.

    Each term word takes its best match in the phrase, weighted by how informative the word is.
    At least half of the term's total weight must be matched.
    """
    if not term or not element:
        return 0.0
    w = [weights.get(t, 1.0) for t in term]
    best = [max(token_match(t, e) for e in element) for t in term]
    total = sum(w)
    matched = sum(wi for wi, b in zip(w, best, strict=True) if b > 0)
    if matched * 2 < total:
        return 0.0
    return sum(wi * b for wi, b in zip(w, best, strict=True)) / total


def _score_career(
    student: StudentView, career: CareerDoc, config: RankingConfig, weights: dict[str, float]
) -> tuple[float, list[Reason]]:
    reasons: list[Reason] = []
    per_field_count: dict[str, int] = {}
    for term in student.terms:
        if per_field_count.get(term.field, 0) >= config.max_terms_per_field:
            continue
        per_field_count[term.field] = per_field_count.get(term.field, 0) + 1
        field_weight = config.field_weights.get(term.field, 0.0)
        best: tuple[float, str, str] | None = None
        for career_field, weight in config.career_field_weights.items():
            for text, tokens in career.fields.get(career_field, ()):
                strength = _phrase_match(term.tokens, tokens, weights)
                value = field_weight * weight * strength
                if value > 0 and (best is None or value > best[0]):
                    best = (value, career_field, text)
        if best is None:
            continue
        value, career_field, text = best
        if term.basis == "observed":
            value *= config.observed_multiplier
        reasons.append(
            Reason(term.field, term.text, term.basis, career_field, text, round(value, 3))
        )
    return round(sum(r.points for r in reasons), 3), reasons


def _stage_info(student_stage: str | None, career: CareerDoc) -> dict[str, Any]:
    needed = career.min_stage
    if needed is None:
        return {"typical_min_stage": None, "status": "not_required", "student_stage": student_stage}
    have = STAGE_RANK.get(student_stage or "")
    if have is None:
        status = "unknown"
    elif have >= STAGE_RANK[needed]:
        status = "meets"
    else:
        status = "below"
    return {"typical_min_stage": needed, "status": status, "student_stage": student_stage}


def _level(points: float, config: RankingConfig) -> Literal["strong", "moderate", "weak"]:
    if points >= config.strong_at:
        return "strong"
    return "moderate" if points >= config.moderate_at else "weak"


def _unknowns(student: StudentView) -> list[str]:
    # Facts we do not hold about any career; stated so nothing is implied by silence.
    unknown = [
        "career_cost_unknown",
        "career_time_needed_unknown",
        "career_location_not_considered",
    ]
    fields = {t.field for t in student.terms}
    for key, code in (
        ("skills", "student_skills_not_told"),
        ("interests", "student_interests_not_told"),
    ):
        if key not in fields:
            unknown.append(code)
    return unknown


def _explore_order(slug: str, seed: str) -> str:
    return hashlib.sha256(f"{seed}:{slug}".encode()).hexdigest()


def rank(
    student: StudentView,
    careers: list[CareerDoc],
    config: RankingConfig | None = None,
    limit: int = 5,
) -> RankResult:
    config = config or RankingConfig()
    weights = word_weights(careers, config.min_word_weight)
    scored: list[tuple[float, CareerDoc, list[Reason]]] = []
    matched_terms: set[tuple[str, str]] = set()
    for career in careers:
        points, reasons = _score_career(student, career, config, weights)
        matched_terms.update((r.student_field, r.student_term) for r in reasons)
        if points > 0:
            if student.stage and _stage_info(student.stage, career)["status"] in (
                "meets",
                "not_required",
            ):
                points = round(points + config.stage_bonus, 3)
            scored.append((points, career, reasons))
    scored.sort(key=lambda s: (-s[0], s[1].slug))

    # Take the best matches but at most `max_per_family` per family; fill any gap afterwards.
    chosen: list[tuple[float, CareerDoc, list[Reason]]] = []
    per_family: dict[str, int] = {}
    deferred = []
    for item in scored:
        family = item[1].family
        if len(chosen) < limit and per_family.get(family, 0) < config.max_per_family:
            chosen.append(item)
            per_family[family] = per_family.get(family, 0) + 1
        else:
            deferred.append(item)
    chosen += deferred[: max(0, limit - len(chosen))]

    unknowns = _unknowns(student)
    recs = [
        Recommendation(
            slug=c.slug,
            family=c.family,
            kind="match",
            points=points,
            match_level=_level(points, config),
            reasons=reasons,
            stage=_stage_info(student.stage, c),
            unknowns=unknowns,
        )
        for points, c, reasons in chosen
    ]

    # Explore: one career each from families the student did not hit, in a per-student
    # reproducible order, so the list always opens a few doors they did not name.
    covered = {r.family for r in recs}
    explore_pool = sorted(
        (c for c in careers if c.family not in covered),
        key=lambda c: _explore_order(c.slug, student.seed),
    )
    explored_families: set[str] = set()
    for career in explore_pool:
        if len(explored_families) >= config.explore_count:
            break
        if career.family in explored_families:
            continue
        explored_families.add(career.family)
        recs.append(
            Recommendation(
                slug=career.slug,
                family=career.family,
                kind="explore",
                points=None,
                match_level=None,
                reasons=[],
                stage=_stage_info(student.stage, career),
                unknowns=unknowns,
            )
        )

    if not student.terms:
        status = "insufficient_profile"
    elif not scored:
        status = "no_matches"
    else:
        status = "ok"
    unmatched = [
        {"field": t.field, "text": t.text}
        for t in student.terms
        if (t.field, t.text) not in matched_terms
    ]
    return RankResult(
        status=status,
        recommendations=recs,
        families=sorted({r.family for r in recs}),
        unmatched_terms=unmatched,
        config=asdict(config),
    )
