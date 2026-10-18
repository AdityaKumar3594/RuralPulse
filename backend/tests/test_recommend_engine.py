"""Pure ranking tests (no database): scoring, diversity, honesty about thin or odd profiles."""

import json
from pathlib import Path

import pytest

from app.core.text import tokenize
from app.ingestion.bundle import load_bundle
from app.ingestion.loader import _career
from app.modules.recommend.engine import (
    CareerDoc,
    ProfileTerm,
    RankingConfig,
    StudentView,
    rank,
    token_match,
)
from app.modules.recommend.service import career_doc

REAL_SEED = Path(__file__).resolve().parents[2] / "data" / "seed"


def phrases(items):
    return tuple((t, tuple(tokenize(t))) for t in items)


def doc(
    slug,
    family="agriculture",
    keywords=(),
    title=(),
    skills=(),
    activities=(),
    desc=(),
    min_stage=None,
):
    return CareerDoc(
        slug=slug,
        family=family,
        fields={
            "keywords": phrases(keywords),
            "title": phrases(title or [slug.replace("-", " ")]),
            "skills": phrases(skills),
            "activities": phrases(activities),
            "description": phrases(desc),
        },
        min_stage=min_stage,
    )


def student(stage=None, seed="s1", basis="reported", **fields):
    terms = [
        ProfileTerm(f, text, tuple(tokenize(text)), basis if isinstance(basis, str) else basis[f])
        for f, items in fields.items()
        for text in items
    ]
    return StudentView(tuple(terms), stage, seed)


def slugs(result, kind="match"):
    return [r.slug for r in result.recommendations if r.kind == kind]


# --- word matching ---


def test_token_match_exact_stem_and_non_match():
    assert token_match("farm", "farm") == 1.0
    assert token_match("farm", "farming") == 0.7  # shorter is a stem of the longer
    assert token_match("விவசாய", "விவசாயம்") == 0.7  # works for Tamil too
    assert token_match("car", "card") == 0.0  # stem shorter than 4 characters is too weak
    assert token_match("cook", "book") == 0.0


# --- scoring: every point is explained ---


def test_points_are_the_sum_of_reasons_and_use_the_configured_weights():
    careers = [
        doc("dairy", keywords=["cow milk"], skills=["animal care"]),
        doc("other", keywords=["x"]),
    ]
    r = rank(student(goals=["cow milk"], skills=["animal care"]), careers)
    top = r.recommendations[0]
    assert top.slug == "dairy"
    assert [(x.student_field, x.career_field, x.points) for x in top.reasons] == [
        ("goals", "keywords", 3.0),  # goals weight 3.0 x keywords 1.0 x full match
        ("skills", "skills", 1.6),  # skills weight 2.0 x career skills 0.8
    ]
    assert top.points == pytest.approx(sum(x.points for x in top.reasons))


def test_goals_count_more_than_interests_and_observed_more_than_reported():
    careers = [
        doc("a", keywords=["alpha"]),
        doc("b", keywords=["beta"]),
        doc("c", keywords=["gamma"]),
    ]
    r = rank(student(goals=["alpha"], interests=["beta"]), careers)
    assert slugs(r)[:2] == ["a", "b"]
    seen = student(basis="observed", skills=["gamma"])
    told = student(basis="reported", skills=["gamma"])
    assert rank(seen, careers).recommendations[0].points == pytest.approx(
        1.5 * rank(told, careers).recommendations[0].points
    )


def test_a_career_with_no_match_is_never_listed_as_a_match():
    r = rank(
        student(interests=["alpha"]), [doc("a", keywords=["alpha"]), doc("z", keywords=["zzz"])]
    )
    assert slugs(r) == ["a"] and "z" not in slugs(r)


def test_multi_word_terms_need_at_least_half_the_informative_words():
    careers = [
        doc("bikes", keywords=["fixing bikes"]),
        doc("fix", keywords=["fixing"]),
        doc("x", keywords=["other"]),
    ]
    r = rank(student(interests=["fixing bikes"]), careers)
    by_slug = {x.slug: x.points for x in r.recommendations if x.kind == "match"}
    # The full phrase beats a partial hit on one word (which may be rejected as too weak).
    assert by_slug["bikes"] > by_slug.get("fix", 0)


def test_common_words_do_not_create_matches():
    # "using" appears in most careers, so it carries little weight; a term that only shares it
    # with a career must not match.
    careers = [doc(f"c{i}", activities=["using tools"]) for i in range(8)] + [
        doc("phones", keywords=["phone repair"])
    ]
    r = rank(student(interests=["using a phone"]), careers)
    assert slugs(r) == ["phones"]


def test_hypotheses_never_reach_the_ranker_but_unmatched_terms_are_reported():
    r = rank(student(interests=["alpha", "astronaut"]), [doc("a", keywords=["alpha"])])
    assert r.unmatched_terms == [{"field": "interests", "text": "astronaut"}]


def test_max_terms_per_field_bounds_the_influence_of_long_lists():
    careers = [doc("a", keywords=[f"w{i}" for i in range(30)])]
    many = student(interests=[f"w{i}" for i in range(30)])
    capped = rank(many, careers, RankingConfig(max_terms_per_field=3)).recommendations[0]
    assert len(capped.reasons) == 3


# --- education stage informs, never excludes ---


def test_stage_never_removes_a_career_and_only_adds_a_small_bonus_when_reachable():
    careers = [
        doc("now", keywords=["alpha"], min_stage="class_10"),
        doc("later", keywords=["alpha"], min_stage="class_12"),
    ]
    r = rank(student(stage="class_10", interests=["alpha"]), careers)
    by = {x.slug: x for x in r.recommendations if x.kind == "match"}
    assert set(by) == {"now", "later"}  # the harder career is still shown
    assert by["now"].stage["status"] == "meets" and by["later"].stage["status"] == "below"
    assert by["now"].points == pytest.approx(by["later"].points + 0.5)
    unknown = rank(student(stage=None, interests=["alpha"]), careers)
    assert {x.stage["status"] for x in unknown.recommendations} == {"unknown"}
    assert (
        rank(student(interests=["alpha"]), [doc("n", keywords=["alpha"])])
        .recommendations[0]
        .stage["status"]
        == "not_required"
    )


def test_stage_bonus_can_be_switched_off():
    c = [doc("now", keywords=["alpha"], min_stage="class_10")]
    base = rank(student(stage="class_10", interests=["alpha"]), c, RankingConfig(stage_bonus=0.0))
    assert base.recommendations[0].points == 2.0


# --- diversity ---


def test_no_family_dominates_when_others_match():
    careers = [doc(f"farm{i}", "agriculture", keywords=["farming"]) for i in range(5)]
    careers += [
        doc("sew", "creative_crafts", keywords=["farming"], skills=[]),
        doc("fix", "skilled_trades", keywords=["farming"]),
    ]
    r = rank(student(interests=["farming"]), careers, limit=4)
    families = [x.family for x in r.recommendations if x.kind == "match"]
    assert families.count("agriculture") == 2 and len(families) == 4


def test_the_cap_relaxes_only_to_fill_the_list_when_nothing_else_matches():
    careers = [doc(f"farm{i}", "agriculture", keywords=["farming"]) for i in range(5)]
    r = rank(student(interests=["farming"]), careers, limit=4)
    assert len(slugs(r)) == 4  # better a full list of one family than an artificially short one


def test_explore_picks_come_from_other_families_and_are_reproducible_per_student():
    families = [
        "agriculture",
        "skilled_trades",
        "health_care",
        "education",
        "business",
        "technology",
    ]
    careers = [
        doc(f"{f}-{i}", f, keywords=["farming"] if f == "agriculture" else ["q"])
        for f in families
        for i in range(2)
    ]
    a = rank(student(interests=["farming"], seed="alice"), careers)
    again = rank(student(interests=["farming"], seed="alice"), careers)
    assert a == again
    explored = [x for x in a.recommendations if x.kind == "explore"]
    assert len(explored) == 2 and len({x.family for x in explored}) == 2
    assert all(x.family != "agriculture" for x in explored)
    assert all(x.points is None and x.match_level is None and x.reasons == [] for x in explored)
    picks = {
        tuple(slugs(rank(student(interests=["farming"], seed=str(i)), careers), "explore"))
        for i in range(20)
    }
    assert len(picks) > 2  # different students get different doors opened


def test_empty_and_unmatched_profiles_are_reported_honestly():
    careers = [
        doc("a", "agriculture", keywords=["alpha"]),
        doc("b", "education", keywords=["beta"]),
        doc("c", "business", keywords=["gamma"]),
    ]
    empty = rank(student(), careers)
    assert (
        empty.status == "insufficient_profile"
        and slugs(empty) == []
        and len(slugs(empty, "explore")) == 2
    )
    odd = rank(student(interests=["zzz qqq"]), careers)
    assert odd.status == "no_matches" and slugs(odd) == [] and len(slugs(odd, "explore")) == 2
    assert odd.unmatched_terms == [{"field": "interests", "text": "zzz qqq"}]


def test_match_levels_follow_the_configured_thresholds():
    c = [doc("a", keywords=["alpha"])]
    low = rank(
        student(interests=["alpha"]), c, RankingConfig(moderate_at=5, strong_at=9)
    ).recommendations[0]
    assert low.match_level == "weak"
    high = rank(
        student(goals=["alpha"]), c, RankingConfig(moderate_at=1, strong_at=3)
    ).recommendations[0]
    assert high.match_level == "strong"


# --- configuration ---


def test_overrides_change_weights_and_are_validated():
    c = RankingConfig.from_overrides(
        {"field_weights.goals": 10, "stage_bonus": 0, "max_per_family": 1}
    )
    assert c.field_weights["goals"] == 10 and c.field_weights["interests"] == 2.0
    assert c.stage_bonus == 0 and c.max_per_family == 1
    for bad in (
        {"nonsense": 1},
        {"field_weights.nope": 1},
        {"stage_bonus": -1},
        {"max_per_family": 0},
    ):
        with pytest.raises(ValueError):
            RankingConfig.from_overrides(bad)
    # a weight override really changes the ranking
    careers = [doc("a", keywords=["alpha"]), doc("b", keywords=["beta"])]
    view = student(goals=["alpha"], interests=["beta"])
    boosted = RankingConfig.from_overrides({"field_weights.interests": 10})
    assert slugs(rank(view, careers, boosted))[0] == "b"


def test_result_is_deterministic_and_json_serialisable_and_has_no_probability_field():
    careers = [doc("a", keywords=["alpha"]), doc("b", "education", keywords=["beta"])]
    view = student(interests=["alpha"])
    first, second = rank(view, careers), rank(view, careers)
    assert first == second
    text = json.dumps(first.to_dict())
    assert "probability" not in text and "confidence" not in text and "chance" not in text


# --- quality on the real catalog ---


@pytest.fixture(scope="module")
def real_docs():
    return [career_doc(_career(c)) for c in load_bundle(REAL_SEED).careers]


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"interests": ["fixing bikes"]}, "automobile-mechanic"),
        ({"goals": ["மாடு வளர்ப்பு"]}, "dairy-farmer"),
        ({"skills": ["stitching"]}, "tailor-fashion-designer"),
        ({"interests": ["விவசாயம்"]}, "crop-farmer"),
        ({"interests": ["cooking"]}, "cook-chef"),
        ({"goals": ["drive"]}, "commercial-driver"),
        ({"interests": ["phone repair"]}, "mobile-phone-repair-technician"),
        ({"skills": ["wiring"]}, "electrician"),
    ],
)
def test_real_catalog_puts_the_obvious_career_first(real_docs, fields, expected):
    r = rank(student(**fields), real_docs)
    assert r.status == "ok" and slugs(r)[0] == expected


def test_real_catalog_never_shows_a_one_family_list_and_always_opens_new_doors(real_docs):
    for fields in (
        {"interests": ["farming", "animals", "crops"]},
        {"interests": ["vehicles", "driving", "engines"]},
    ):
        r = rank(student(**fields), real_docs, limit=5)
        assert len(r.families) >= 3
        assert any(x.kind == "explore" for x in r.recommendations)


def test_real_catalog_is_honest_about_a_goal_it_does_not_cover(real_docs):
    r = rank(student(goals=["astronaut"]), real_docs)
    assert r.status == "no_matches"
    assert r.unmatched_terms == [{"field": "goals", "text": "astronaut"}]
