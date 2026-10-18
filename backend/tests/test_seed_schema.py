from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.ingestion.bundle import SeedError, load_bundle
from app.modules.catalog.seed_schema import CareerSeed
from app.modules.sources.seed_schema import OpportunitySeed, SourceSeed

FIXTURES = Path(__file__).parent / "fixtures" / "seed"
REAL_SEED = Path(__file__).resolve().parents[2] / "data" / "seed"

BASE = {
    "slug": "x",
    "source": "test-portal",
    "kind": "scheme",
    "title": {"en": "T"},
    "summary": {"en": "S"},
    "provider": "P",
    "url": "https://portal.gov.in/x",
}
PROOF = {
    "status": "verified",
    "verified_at": "2026-10-18",
    "verified_by": "t",
    "evidence": [{"url": "https://portal.gov.in/x", "note": "n"}],
}


def opp(**over):
    return OpportunitySeed.model_validate({**BASE, **over})


# --- the "never invent" invariants ---


def test_unverified_record_cannot_carry_structured_claims():
    for claim in (
        {"benefits": [{"text": {"en": "b"}, "amount_inr": 100}]},
        {"application_deadline": "2030-01-01"},
        {"eligibility": {"min_age": 14}},
        {"required_documents": ["Aadhaar"]},
        {"scope": {"level": "state", "states": ["Kerala"]}},
    ):
        with pytest.raises(ValidationError, match="not listed in verification.verified_fields"):
            opp(**claim)


def test_claim_is_accepted_only_when_that_exact_field_is_verified():
    ok = opp(
        benefits=[{"text": {"en": "b"}, "amount_inr": 100}],
        verification={**PROOF, "verified_fields": ["benefit"]},
    )
    assert ok.benefits[0].amount_inr == 100
    with pytest.raises(ValidationError, match="'benefit'"):
        opp(
            benefits=[{"text": {"en": "b"}, "amount_inr": 100}],
            verification={**PROOF, "verified_fields": ["url"]},
        )


def test_verified_status_needs_proof():
    for missing in ("verified_at", "verified_by", "evidence"):
        proof = {k: v for k, v in PROOF.items() if k != missing}
        with pytest.raises(ValidationError, match="need verified_at"):
            opp(verification={**proof, "verified_fields": ["url"]})
    with pytest.raises(ValidationError, match="need verified_at"):
        opp(verification={**PROOF, "verified_fields": []})


def test_unverified_cannot_claim_verified_fields_or_human_review():
    with pytest.raises(ValidationError):
        opp(verification={"status": "unverified", "verified_fields": ["url"]})
    with pytest.raises(ValidationError):
        opp(verification={"status": "unverified", "human_reviewed": True})


def test_urls_must_be_https_and_unknown_keys_are_rejected():
    with pytest.raises(ValidationError, match="https"):
        opp(url="http://portal.gov.in/x")
    with pytest.raises(ValidationError):
        opp(surprise="field")
    with pytest.raises(ValidationError, match="not in allowed_domains"):
        SourceSeed.model_validate(
            {
                "id": "s",
                "name": {"en": "S"},
                "publisher": "P",
                "base_url": "https://evil.example",
                "category": "ministry",
                "allowed_domains": ["portal.gov.in"],
            }
        )


def test_scope_state_rules():
    with pytest.raises(ValidationError):
        opp(scope={"level": "state", "states": []})
    with pytest.raises(ValidationError):
        opp(scope={"level": "national", "states": ["Kerala"]})


def test_career_descriptions_cannot_contain_money_or_statistics():
    base = {
        "slug": "c",
        "family": "agriculture",
        "title": {"en": "C"},
        "description": {"en": "Earns a good living"},
        "activities": {"en": ["a"]},
        "skills": {"en": ["s"]},
        "entry": {"notes": {"en": "n"}},
        "routes": [{"kind": "on_the_job", "title": {"en": "r"}}],
    }
    CareerSeed.model_validate(base)
    for bad in ("Earns Rs. 20 daily", "Pays ₹500", "90% get jobs", "Earns 2 lakh a year"):
        with pytest.raises(ValidationError, match="money amounts"):
            CareerSeed.model_validate({**base, "description": {"en": bad}})


def test_career_localized_lists_must_line_up():
    with pytest.raises(ValidationError, match="same number"):
        CareerSeed.model_validate(
            {
                "slug": "c",
                "family": "agriculture",
                "title": {"en": "C"},
                "description": {"en": "d"},
                "activities": {"en": ["a", "b"], "ta": ["அ"]},
                "skills": {"en": ["s"]},
                "entry": {"notes": {"en": "n"}},
                "routes": [{"kind": "on_the_job", "title": {"en": "r"}}],
            }
        )


# --- bundle cross-checks ---


def copy_fixture(tmp_path: Path, **edits) -> Path:
    for name in ("sources", "opportunities", "careers"):
        data = yaml.safe_load((FIXTURES / f"{name}.yaml").read_text(encoding="utf-8"))
        data = edits.get(name, lambda d: d)(data)
        (tmp_path / f"{name}.yaml").write_text(
            yaml.safe_dump(data, allow_unicode=True), encoding="utf-8"
        )
    return tmp_path


def test_fixture_bundle_is_valid():
    bundle = load_bundle(FIXTURES)
    assert (len(bundle.sources), len(bundle.opportunities), len(bundle.careers)) == (1, 9, 3)


def problems(tmp_path, **edits) -> list[str]:
    with pytest.raises(SeedError) as exc:
        load_bundle(copy_fixture(tmp_path, **edits))
    return exc.value.problems


def test_bundle_rejects_urls_off_the_sources_domain(tmp_path):
    def edit(opps):
        opps[0]["url"] = "https://not-official.example/merit"
        return opps

    assert any("not on source" in p for p in problems(tmp_path, opportunities=edit))


def test_bundle_rejects_unofficial_evidence_hosts(tmp_path):
    def edit(opps):
        opps[0]["verification"]["evidence"][0]["url"] = "https://blog.example.com/post"
        return opps

    assert any("not an official site" in p for p in problems(tmp_path, opportunities=edit))


def test_bundle_rejects_dangling_references_and_duplicates(tmp_path):
    def opps(d):
        d[0]["source"] = "nope"
        d.append(dict(d[1]))
        return d

    def careers(d):
        d[0]["related"] = ["ghost", "electrician"]
        d[0]["routes"][1]["opportunity"] = "ghost-opp"
        d[0]["learning_resources"] = ["ghost-opp"]
        return d

    found = " | ".join(problems(tmp_path, opportunities=opps, careers=careers))
    for expected in (
        "unknown source 'nope'",
        "duplicate opportunity slug",
        "bad related career 'ghost'",
        "bad related career 'electrician'",
        "unknown opportunity 'ghost-opp'",
        "unknown learning resource 'ghost-opp'",
    ):
        assert expected in found


def test_bundle_reports_every_problem_at_once(tmp_path):
    def opps(d):
        d[0]["url"] = "http://x"
        d[1]["unknown_key"] = 1
        return d

    assert len(problems(tmp_path, opportunities=opps)) >= 2


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(SeedError, match="careers.yaml: file not found"):
        load_bundle(tmp_path)


# --- the real seed data ---


@pytest.fixture(scope="module")
def real():
    return load_bundle(REAL_SEED)


def test_real_seed_is_valid_and_consistent(real):
    assert real.sources and real.opportunities and real.careers


def test_every_verified_real_record_has_evidence_and_is_not_marked_human_reviewed(real):
    for o in real.opportunities:
        v = o.verification
        if v.status == "verified":
            assert v.evidence and v.verified_fields and v.verified_by, o.slug
        # Nobody has re-checked these yet; this flips only when a person does so.
        assert v.human_reviewed is False, o.slug


def test_real_careers_are_diverse(real):
    families = [c.family for c in real.careers]
    assert len(set(families)) == 10
    for family in set(families):
        assert families.count(family) >= 2
    tech_share = families.count("technology") / len(families)
    assert tech_share <= 0.2  # software must not dominate the catalog
    slugs = {c.slug for c in real.careers}
    assert {"electrician", "nurse"} <= slugs or len(slugs) >= 25


def test_real_careers_have_tamil_text_and_no_dangling_links(real):
    for c in real.careers:
        assert c.title.get("ta") and c.description.get("ta"), c.slug
        assert c.activities.get("ta") and c.skills.get("ta"), c.slug
        assert len(c.related) >= 1


# --- command line ---


def test_cli_validate_succeeds_on_good_data_and_reports_problems_on_bad(tmp_path, capsys):
    from app.ingestion.cli import main

    assert main(["validate", "--dir", str(FIXTURES)]) == 0
    assert "valid: 1 sources, 9 opportunities, 3 careers" in capsys.readouterr().out
    assert main(["validate", "--dir", str(tmp_path)]) == 1
    assert "file not found" in capsys.readouterr().err
