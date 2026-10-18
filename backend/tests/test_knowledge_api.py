from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.ingestion.bundle import load_bundle
from app.ingestion.loader import build_search_text, upsert_bundle
from app.modules.retrieval import service as retrieval
from app.modules.retrieval.service import Filters, tokenize
from app.modules.sources.freshness import freshness
from app.modules.sources.models import Opportunity, Publication, Verification
from tests.conftest import FIXTURE_SEED


def find(client, **params):
    r = client.get("/api/search", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def ids(body):
    return [h["id"] for h in body["results"]]


# --- tokenizer ---


def test_tokenize_keeps_tamil_words_and_drops_punctuation_and_stopwords():
    assert tokenize("How can I get a scholarship?") == ["get", "scholarship"]
    assert tokenize("விவசாயம், மாடு வளர்ப்பு!") == ["விவசாயம்", "மாடு", "வளர்ப்பு"]
    assert tokenize("a the of") == [
        "a",
        "the",
        "of",
    ]  # only stopwords: keep them rather than nothing
    assert tokenize(None) == [] and tokenize("  ?! ") == []


def test_tokenize_neutralises_tsquery_syntax():
    for token in tokenize("welding' | drop & table ! (x) :*"):
        assert all(c.isalnum() for c in token), token


def test_search_text_flattens_localized_content():
    text = build_search_text({"en": "Farmer", "ta": "விவசாயி"}, ["Crops", "பயிர்"], None)
    assert text == "farmer விவசாயி crops பயிர்"


# --- freshness ---


def make_opp(**over):
    base = {
        "slug": "x",
        "source_id": "s",
        "kind": "scheme",
        "title": {"en": "t"},
        "summary": {"en": "s"},
        "provider": "p",
        "url": "https://a.gov.in",
        "scope": {"level": "national", "states": []},
        "verification_status": Verification.VERIFIED,
        "verified_at": date(2026, 10, 18),
    }
    return Opportunity(**{**base, **over})


@pytest.mark.parametrize(
    ("over", "today", "expected"),
    [
        ({}, date(2026, 10, 19), "fresh"),
        ({}, date(2026, 10, 18) + timedelta(days=180), "fresh"),  # boundary: exactly 180 days
        ({}, date(2026, 10, 18) + timedelta(days=181), "stale"),
        (
            {"verification_status": Verification.UNVERIFIED, "verified_at": None},
            date(2026, 10, 19),
            "unverified",
        ),
        ({"application_deadline": date(2026, 10, 1)}, date(2026, 10, 19), "expired"),
        (
            {"application_deadline": date(2026, 10, 19)},
            date(2026, 10, 19),
            "fresh",
        ),  # deadline day itself
        ({"expires_on": date(2026, 10, 1)}, date(2026, 10, 19), "expired"),
        ({"verified_at": None}, date(2026, 10, 19), "stale"),
    ],
)
def test_freshness_rules(over, today, expected):
    assert freshness(make_opp(**over), today, 180) == expected


# --- loader ---


def test_loading_is_idempotent_and_reports_counts(seeded, db):
    again = upsert_bundle(db, load_bundle(FIXTURE_SEED))
    assert again == {"sources": 1, "opportunities": 9, "careers": 3}
    assert len(db.scalars(select(Opportunity)).all()) == 9


def test_loader_never_upgrades_verification(seeded, db):
    welding = db.get(Opportunity, "unverified-welding-course")
    assert welding.verification_status is Verification.UNVERIFIED
    assert welding.verified_fields == [] and welding.verified_at is None
    assert welding.human_reviewed is False


def test_loaded_records_keep_provenance(seeded, db):
    scholarship = db.get(Opportunity, "fresh-scholarship")
    assert scholarship.evidence[0]["url"].startswith("https://portal.gov.in/")
    assert scholarship.verified_by == "test-fixture" and scholarship.retrieved_at is not None


# --- search ---


def test_exact_match_ranks_first_and_carries_source_and_verification(seeded):
    body = find(seeded, q="merit scholarship")
    top = body["results"][0]
    assert body["status"] == "ok" and body["search_mode"] == "keyword"
    assert (top["id"], top["match_type"]) == ("fresh-scholarship", "exact")
    assert top["source"]["id"] == "test-portal" and top["url"] == "https://portal.gov.in/merit"
    assert top["freshness"] == "fresh"
    assert top["verification"]["status"] == "verified"
    assert top["verification"]["evidence"][0]["note"] == "fixture"
    assert top["eligibility_known"] is True


def test_prefix_and_misspelling_are_partial_not_exact(seeded):
    prefix = find(seeded, q="scholar")
    assert ids(prefix) == ["fresh-scholarship"] and prefix["results"][0]["match_type"] == "partial"
    assert prefix["status"] == "partial_only"
    typo = find(seeded, q="scholarshpi")
    assert "fresh-scholarship" in ids(typo)
    assert all(h["match_type"] == "partial" for h in typo["results"])
    assert "electrician" in ids(find(seeded, q="electrcian"))


def test_lookalike_words_do_not_count_as_matches(seeded):
    # "scholar" is not "school", "training" is not "trade": these were false positives at 0.5.
    assert ids(find(seeded, q="scholar")) == ["fresh-scholarship"]
    assert find(seeded, q="training")["status"] == "insufficient_evidence"


def test_tamil_queries_find_tamil_and_english_records(seeded):
    body = find(seeded, q="உதவித்தொகை", language="ta")
    assert ids(body)[0] == "fresh-scholarship"
    assert body["results"][0]["title"] == "மாணவர்களுக்கான தகுதி உதவித்தொகை"
    assert "dairy-farmer" in ids(find(seeded, q="விவசாயம்", language="ta"))


def test_careers_and_opportunities_are_searched_together_with_type_filter(seeded):
    both = find(seeded, q="skill")
    assert {h["type"] for h in both["results"]} == {"opportunity"}
    mixed = find(seeded, q="farming")
    assert [(h["type"], h["id"]) for h in mixed["results"]] == [("career", "dairy-farmer")]
    assert find(seeded, q="farming", type="opportunity")["status"] == "insufficient_evidence"
    only_careers = find(seeded, type="career")
    assert {h["type"] for h in only_careers["results"]} == {"career"}


def test_no_match_says_insufficient_evidence_instead_of_guessing(seeded):
    body = find(seeded, q="astronaut training abroad")
    assert body["results"] == []
    assert body["status"] == "insufficient_evidence"
    assert "Nothing is guessed" in body["message"]


def test_hostile_queries_are_harmless(seeded):
    for q in ("'; DROP TABLE opportunities; --", "a & b | !c :* (", "\\", "%_", "x" * 200):
        body = find(seeded, q=q)
        assert body["status"] in {"ok", "partial_only", "insufficient_evidence"}
    assert find(seeded, q="scholarship")["status"] == "ok"  # table still there


def test_browse_mode_without_query_lists_by_filters(seeded):
    body = find(seeded, kind="scholarship")
    assert ids(body) == ["fresh-scholarship"] and body["results"][0]["match_type"] == "browse"


def test_expired_records_are_hidden_unless_requested_and_are_flagged(seeded):
    assert "expired-apprenticeship" not in ids(find(seeded, q="apprenticeship"))
    shown = find(seeded, q="apprenticeship", include_expired="true")
    hit = shown["results"][0]
    assert hit["id"] == "expired-apprenticeship"
    assert hit["freshness"] == "expired" and "expired_or_deadline_passed" in hit["flags"]


def test_unverified_records_are_flagged_and_can_be_excluded(seeded):
    hit = find(seeded, q="welding")["results"][0]
    assert hit["freshness"] == "unverified" and "unverified" in hit["flags"]
    assert hit["verification"]["verified_fields"] == []
    assert (
        find(seeded, q="welding", include_unverified="false")["status"] == "insufficient_evidence"
    )


def test_stale_records_stay_visible_but_flagged(seeded, db):
    later = date.today() + timedelta(days=181)  # one day past the freshness window
    body = retrieval.search(
        db, "merit", lang="en", filters=Filters(), limit=10, fresh_days=180, today=later
    )
    hit = body["results"][0]
    assert hit["freshness"] == "stale" and "needs_reverification" in hit["flags"]


def test_state_filter_drops_only_explicitly_other_states(seeded):
    tn = ids(find(seeded, q="skill", state="Tamil Nadu"))
    assert tn == ["tamil-nadu-skilling"]
    kerala = ids(find(seeded, q="skill", state="kerala"))  # case-insensitive
    assert kerala == ["kerala-only-programme"]
    # National records are never dropped by a state filter.
    assert "national-learning-platform" in ids(find(seeded, q="lessons", state="Kerala"))


def test_stage_filter_drops_only_records_that_state_other_stages(seeded):
    assert "fresh-scholarship" in ids(find(seeded, q="scholarship", stage="class_10"))
    assert "fresh-scholarship" not in ids(find(seeded, q="scholarship", stage="graduate"))
    # No stated stages = unknown, not negative: kept, and marked as not known.
    unknown = find(seeded, q="lessons", stage="graduate")["results"][0]
    assert unknown["id"] == "national-learning-platform" and unknown["eligibility_known"] is False
    assert "eligibility_not_verified" in unknown["flags"]


def test_family_and_kind_filters_select_the_right_record_types(seeded):
    assert ids(find(seeded, family="agriculture")) == ["dairy-farmer"]
    assert find(seeded, family="agriculture")["results"][0]["type"] == "career"
    assert {h["type"] for h in find(seeded, kind="platform")["results"]} == {"opportunity"}


def test_withdrawn_records_are_never_returned(seeded, db):
    db.get(Opportunity, "fresh-scholarship").publication_status = Publication.WITHDRAWN
    db.commit()
    assert "fresh-scholarship" not in ids(find(seeded, q="scholarship"))
    assert seeded.get("/api/opportunities/fresh-scholarship").status_code == 404


def test_limit_and_validation(seeded):
    assert len(find(seeded, limit=2)["results"]) == 2
    assert seeded.get("/api/search", params={"limit": 0}).status_code == 422
    assert seeded.get("/api/search", params={"kind": "nonsense"}).status_code == 422
    assert seeded.get("/api/search", params={"language": "fr"}).status_code == 422
    assert seeded.get("/api/search", params={"q": "x" * 201}).status_code == 422


def test_missing_translation_falls_back_to_english_and_says_so(seeded):
    hit = find(seeded, q="platform", language="ta")["results"][0]
    assert hit["id"] == "national-learning-platform"
    assert hit["title"] == "National learning platform" and hit["language_fallback"] is True
    translated = find(seeded, q="உதவித்தொகை", language="ta")["results"][0]
    assert translated["language_fallback"] is False


# --- detail endpoints ---


def test_opportunity_detail_exposes_claims_with_their_verification(seeded):
    body = seeded.get("/api/opportunities/fresh-scholarship").json()
    assert body["benefits"][0]["amount_inr"] == 12000
    assert body["eligibility"]["max_family_income_inr_per_year"] == 100000
    assert body["verification"]["verified_fields"] == [
        "url",
        "provider",
        "eligibility",
        "benefit",
        "deadline",
    ]
    assert body["freshness"] == "fresh" and "not_human_reviewed" in body["flags"]
    assert body["source"]["name"] == "Test Portal"


def test_unverified_detail_has_no_claims_to_misquote(seeded):
    body = seeded.get("/api/opportunities/unverified-welding-course").json()
    assert (
        body["benefits"] == []
        and body["eligibility"] is None
        and body["application_deadline"] is None
    )
    assert body["flags"][0] == "unverified" or "unverified" in body["flags"]
    assert seeded.get("/api/opportunities/nope").status_code == 404


def test_career_detail_resolves_routes_related_and_resources(seeded):
    body = seeded.get("/api/careers/electrician?language=ta").json()
    assert body["title"] == "மின்பணியாளர்"
    # One route title and the linked platform have no Tamil, so the response must say so.
    assert body["language_fallback"] is True
    assert seeded.get("/api/careers/dairy-farmer?language=ta").json()["language_fallback"] is False
    assert body["entry"]["typical_min_stage"] == "class_10"
    assert body["routes"][1]["opportunity"]["slug"] == "national-learning-platform"
    assert body["related"] == [{"slug": "tailor", "family": "creative_crafts", "title": "Tailor"}]
    assert [r["slug"] for r in body["learning_resources"]] == ["national-learning-platform"]
    assert body["verification_status"] == "unverified" and body["human_reviewed"] is False
    assert seeded.get("/api/careers/ghost").status_code == 404


def test_career_without_tamil_falls_back_and_flags_it(seeded):
    body = seeded.get("/api/careers/tailor?language=ta").json()
    assert body["title"] == "Tailor" and body["language_fallback"] is True


def test_career_list_and_family_filter(seeded):
    assert {c["slug"] for c in seeded.get("/api/careers").json()} == {
        "electrician",
        "dairy-farmer",
        "tailor",
    }
    assert [c["slug"] for c in seeded.get("/api/careers?family=agriculture").json()] == [
        "dairy-farmer"
    ]
    assert seeded.get("/api/careers?family=astronomy").status_code == 422


def test_sources_endpoint_lists_the_registry(seeded):
    [src] = seeded.get("/api/sources").json()
    assert src["id"] == "test-portal" and src["api_access"] == "none_found"


def test_knowledge_endpoints_are_public_but_personal_data_is_not_involved(seeded):
    # No Authorization header anywhere above: the catalog holds no student data.
    assert seeded.get("/api/search?q=merit").status_code == 200
