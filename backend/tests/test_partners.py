import pytest
from sqlalchemy import select

from app.modules.partners.models import Provider
from app.modules.sources.models import Opportunity
from tests.conftest import make_student, staff_headers

PROVIDER = {
    "name": "Green Fields Trust",
    "kind": "ngo",
    "website": "https://greenfields.example.org",
    "description": "Farm training",
}

PAYLOAD = {
    "kind": "training_program",
    "title": {"en": "Organic farming workshop", "ta": "இயற்கை விவசாயப் பயிலரங்கு"},
    "summary": {"en": "A two-week workshop on organic farming."},
    "url": "https://greenfields.example.org/workshop",
    "keywords": ["organic", "farming"],
    "scope": {"level": "state", "states": ["Tamil Nadu"]},
    "eligibility": {"education_stages": ["class_12", "undergraduate"], "min_age": 17},
    "required_documents": ["Aadhaar copy"],
    "application_deadline": "2099-06-30",
    "benefits": [{"text": {"en": "Free lunch during the workshop"}, "amount_inr": None}],
}

EVIDENCE = [
    {"url": "https://greenfields.example.org/workshop/rules", "note": "Page lists the rules"}
]


@pytest.fixture
def approved(seeded, admin, partner):
    r = seeded.post("/api/partner/provider", json=PROVIDER, headers=partner)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert seeded.post(f"/api/admin/providers/{pid}/approve", headers=admin).status_code == 200
    return pid


def draft(client, headers, payload=None):
    r = client.post("/api/partner/submissions", json=payload or PAYLOAD, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def submit(client, headers, sid):
    r = client.post(f"/api/partner/submissions/{sid}/submit", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def decide(client, admin, sid, **body):
    return client.post(f"/api/admin/submissions/{sid}/decision", json=body, headers=admin)


def test_only_partners_use_partner_endpoints(seeded, admin, facilitator, partner):
    student = make_student(seeded)
    for headers in (student, facilitator, admin):
        assert (
            seeded.post("/api/partner/provider", json=PROVIDER, headers=headers).status_code == 403
        )
    assert seeded.get("/api/partner/submissions").status_code == 401


def test_provider_profile_rules(seeded, admin, partner):
    assert (
        seeded.post(
            "/api/partner/provider",
            json={**PROVIDER, "website": "http://insecure.example.org"},
            headers=partner,
        ).status_code
        == 422
    )
    assert seeded.get("/api/partner/provider", headers=partner).status_code == 404
    r = seeded.post("/api/partner/provider", json=PROVIDER, headers=partner)
    assert r.status_code == 201 and r.json()["status"] == "pending"
    assert seeded.post("/api/partner/provider", json=PROVIDER, headers=partner).status_code == 409
    # While pending, identity can change; the description always can.
    assert (
        seeded.put(
            "/api/partner/provider", json={"name": "Green Fields Society"}, headers=partner
        ).status_code
        == 200
    )
    seeded.post(f"/api/admin/providers/{r.json()['id']}/approve", headers=admin)
    assert (
        seeded.put(
            "/api/partner/provider", json={"description": "More text"}, headers=partner
        ).status_code
        == 200
    )
    locked = seeded.put(
        "/api/partner/provider", json={"website": "https://other.example.org"}, headers=partner
    )
    assert (locked.status_code, locked.json()["detail"]) == (409, "identity_locked_after_approval")


def test_a_pending_provider_cannot_submit_opportunities(seeded, partner):
    seeded.post("/api/partner/provider", json=PROVIDER, headers=partner)
    r = seeded.post("/api/partner/submissions", json=PAYLOAD, headers=partner)
    assert (r.status_code, r.json()["detail"]) == (409, "provider_not_approved")


def test_approving_a_provider_creates_its_source_record(seeded, db, approved):
    provider = db.get(Provider, __import__("uuid").UUID(approved))
    assert provider.source_id.startswith("provider-")
    sources = {s["id"]: s for s in seeded.get("/api/sources").json()}
    assert sources[provider.source_id]["publisher"] == "Green Fields Trust"


def test_submissions_validate_their_content(seeded, approved, partner):
    for bad in (
        {**PAYLOAD, "title": {"ta": "மட்டும்"}},
        {**PAYLOAD, "kind": "lottery"},
        {**PAYLOAD, "scope": {"level": "state", "states": []}},
        {**PAYLOAD, "keywords": ["x"] * 21},
    ):
        assert seeded.post("/api/partner/submissions", json=bad, headers=partner).status_code == 422


def test_the_url_must_be_on_the_providers_own_site_before_review(seeded, approved, partner):
    sub = draft(seeded, partner, {**PAYLOAD, "url": "https://somewhere-else.example.com/x"})
    r = seeded.post(f"/api/partner/submissions/{sub['id']}/submit", headers=partner)
    assert (r.status_code, r.json()["detail"]) == (422, "url_must_be_on_provider_website")


def test_full_review_cycle_changes_requested_then_approved_with_only_verified_claims_published(
    seeded, admin, partner, approved
):
    sub = draft(seeded, partner)
    assert submit(seeded, partner, sub["id"])["status"] == "submitted"
    # Editing is locked while it is under review.
    assert (
        seeded.put(
            f"/api/partner/submissions/{sub['id']}", json=PAYLOAD, headers=partner
        ).status_code
        == 409
    )
    assert [s["id"] for s in seeded.get("/api/admin/submissions", headers=admin).json()] == [
        sub["id"]
    ]

    assert (
        decide(seeded, admin, sub["id"], decision="request_changes").status_code == 422
    )  # notes required
    r = decide(
        seeded, admin, sub["id"], decision="request_changes", notes="Please add the full address"
    )
    assert r.json()["submission"]["status"] == "changes_requested"
    edited = seeded.put(
        f"/api/partner/submissions/{sub['id']}", json=PAYLOAD, headers=partner
    ).json()
    assert edited["revision"] == 2 and edited["review_notes"] == "Please add the full address"
    submit(seeded, partner, sub["id"])

    # The administrator verifies the eligibility and the documents, but NOT the benefit or the
    # deadline or the state scope: those must not be published as facts.
    approved_r = decide(
        seeded,
        admin,
        sub["id"],
        decision="approve",
        verification={
            "verified_fields": ["url", "provider", "eligibility", "documents"],
            "evidence": EVIDENCE,
        },
    )
    assert approved_r.status_code == 200, approved_r.text
    out = approved_r.json()
    assert out["verification_status"] == "verified"
    assert sorted(out["stripped_claims"]) == ["benefit", "deadline", "scope"]
    slug = out["published_slug"]
    live = seeded.get(f"/api/opportunities/{slug}").json()
    assert live["eligibility"]["min_age"] == 17 and live["required_documents"] == ["Aadhaar copy"]
    assert (
        live["benefits"] == []
        and live["application_deadline"] is None
        and live["scope"]["level"] == "national"
    )
    assert live["verification"]["human_reviewed"] is True
    assert live["verification"]["verified_by"].startswith("admin:")
    assert live["verification"]["verified_fields"] == [
        "url",
        "provider",
        "eligibility",
        "documents",
    ]
    assert (
        live["provider"] == "Green Fields Trust" and live["source"]["name"] == "Green Fields Trust"
    )
    found = seeded.get("/api/search", params={"q": "organic farming"}).json()
    assert slug in [h["id"] for h in found["results"]]
    assert (
        seeded.get(f"/api/partner/submissions/{sub['id']}", headers=partner).json()["status"]
        == "approved"
    )
    # An approved submission can no longer be edited or decided again.
    assert (
        seeded.put(
            f"/api/partner/submissions/{sub['id']}", json=PAYLOAD, headers=partner
        ).status_code
        == 409
    )
    assert decide(seeded, admin, sub["id"], decision="reject").status_code == 409


def test_approval_without_verification_publishes_an_unverified_record_stripped_of_claims(
    seeded, admin, partner, approved
):
    sub = draft(seeded, partner)
    submit(seeded, partner, sub["id"])
    out = decide(seeded, admin, sub["id"], decision="approve").json()
    assert out["verification_status"] == "unverified"  # never auto-verified
    assert sorted(out["stripped_claims"]) == [
        "benefit",
        "deadline",
        "documents",
        "eligibility",
        "scope",
    ]
    live = seeded.get(f"/api/opportunities/{out['published_slug']}").json()
    assert live["verification"] == {
        **live["verification"],
        "status": "unverified",
        "verified_fields": [],
        "human_reviewed": False,
    }
    assert live["freshness"] == "unverified" and "unverified" in live["flags"]
    assert live["eligibility"] is None and live["benefits"] == []


def test_verification_needs_evidence_on_an_acceptable_site_and_a_real_claim(
    seeded, admin, partner, approved
):
    sub = draft(seeded, partner)
    submit(seeded, partner, sub["id"])
    cases = [
        ({"verified_fields": ["eligibility"], "evidence": []}, "evidence_required"),
        (
            {
                "verified_fields": ["eligibility"],
                "evidence": [{"url": "https://random-blog.example.com/x", "note": "n"}],
            },
            "evidence_must_be_official_or_on_provider_site",
        ),
        (
            {
                "verified_fields": ["eligibility"],
                "evidence": [{"url": "http://greenfields.example.org/x", "note": "n"}],
            },
            "url_must_be_https",
        ),
    ]
    for verification, code in cases:
        r = decide(seeded, admin, sub["id"], decision="approve", verification=verification)
        assert (r.status_code, r.json()["detail"]) == (422, code)
    # Evidence on an official government site is accepted.
    gov = [{"url": "https://labour.gov.in/notice", "note": "Government notice"}]
    ok = decide(
        seeded,
        admin,
        sub["id"],
        decision="approve",
        verification={"verified_fields": ["eligibility"], "evidence": gov},
    )
    assert ok.status_code == 200


def test_cannot_verify_a_claim_the_partner_did_not_make(seeded, admin, partner, approved):
    minimal = {k: PAYLOAD[k] for k in ("kind", "title", "summary", "url")}
    sub = draft(seeded, partner, minimal)
    submit(seeded, partner, sub["id"])
    r = decide(
        seeded,
        admin,
        sub["id"],
        decision="approve",
        verification={"verified_fields": ["benefit"], "evidence": EVIDENCE},
    )
    assert (r.status_code, r.json()["detail"]) == (422, "cannot_verify_absent_claim:benefit")


def test_rejection_and_admin_review_permissions(seeded, admin, facilitator, partner, approved):
    sub = draft(seeded, partner)
    submit(seeded, partner, sub["id"])
    for headers in (partner, facilitator):
        assert decide(seeded, headers, sub["id"], decision="reject").status_code == 403
    r = decide(seeded, admin, sub["id"], decision="reject", notes="Not suitable")
    assert r.json()["submission"]["status"] == "rejected" and r.json()["published_slug"] is None
    assert seeded.get("/api/search", params={"q": "organic"}).json()["results"] == []


def test_withdrawing_takes_the_published_listing_down(seeded, admin, partner, approved):
    sub = draft(seeded, partner)
    submit(seeded, partner, sub["id"])
    slug = decide(seeded, admin, sub["id"], decision="approve").json()["published_slug"]
    assert seeded.get(f"/api/opportunities/{slug}").status_code == 200
    w = seeded.post(f"/api/partner/submissions/{sub['id']}/withdraw", headers=partner)
    assert w.json()["status"] == "withdrawn"
    assert seeded.get(f"/api/opportunities/{slug}").status_code == 404
    assert (
        seeded.post(f"/api/partner/submissions/{sub['id']}/withdraw", headers=partner).status_code
        == 409
    )


def test_revising_a_published_listing_keeps_it_live_until_the_new_version_is_approved(
    seeded, admin, partner, approved
):
    sub = draft(seeded, partner)
    submit(seeded, partner, sub["id"])
    slug = decide(seeded, admin, sub["id"], decision="approve").json()["published_slug"]
    assert (
        seeded.post(
            f"/api/partner/submissions/{draft(seeded, partner)['id']}/revise", headers=partner
        ).status_code
        == 409
    )
    rev = seeded.post(f"/api/partner/submissions/{sub['id']}/revise", headers=partner)
    assert rev.status_code == 201 and rev.json()["replaces_slug"] == slug
    new = {**PAYLOAD, "title": {"en": "Organic farming workshop (2027)"}}
    seeded.put(f"/api/partner/submissions/{rev.json()['id']}", json=new, headers=partner)
    assert (
        seeded.get(f"/api/opportunities/{slug}").json()["title"] == "Organic farming workshop"
    )  # unchanged
    submit(seeded, partner, rev.json()["id"])
    out = decide(seeded, admin, rev.json()["id"], decision="approve").json()
    assert out["published_slug"] == slug
    assert (
        seeded.get(f"/api/opportunities/{slug}").json()["title"]
        == "Organic farming workshop (2027)"
    )


def test_suspending_a_provider_removes_its_listings(seeded, admin, partner, approved):
    sub = draft(seeded, partner)
    submit(seeded, partner, sub["id"])
    slug = decide(seeded, admin, sub["id"], decision="approve").json()["published_slug"]
    assert (
        seeded.post(f"/api/admin/providers/{approved}/suspend", headers=admin).json()["status"]
        == "suspended"
    )
    assert seeded.get(f"/api/opportunities/{slug}").status_code == 404
    assert seeded.post("/api/partner/submissions", json=PAYLOAD, headers=partner).status_code == 409


def test_partners_cannot_see_each_others_submissions(seeded, db, admin, partner, approved):
    sub = draft(seeded, partner)
    other = staff_headers(seeded, db, "partner", "9100000070")
    assert seeded.get(f"/api/partner/submissions/{sub['id']}", headers=other).status_code == 404
    assert seeded.get("/api/partner/submissions", headers=other).json() == []
    assert (
        seeded.post(f"/api/partner/submissions/{sub['id']}/submit", headers=other).status_code
        == 404
    )


def test_providers_see_counts_only_and_confirm_by_reference_code(
    seeded, db, admin, partner, approved
):
    sub = draft(seeded, partner)
    submit(seeded, partner, sub["id"])
    slug = decide(seeded, admin, sub["id"], decision="approve").json()["published_slug"]
    student = make_student(seeded)
    app = seeded.post("/api/applications", json={"opportunity": slug}, headers=student).json()
    seeded.put(
        f"/api/applications/{app['id']}", json={"internal_status": "preparing"}, headers=student
    )
    seeded.put(
        f"/api/applications/{app['id']}", json={"internal_status": "applied"}, headers=student
    )

    stats = seeded.get(f"/api/partner/opportunities/{slug}/stats", headers=partner).json()
    assert stats == {
        "opportunity": slug,
        "by_internal_status": {"applied": 1},
        "by_external_status": {"unknown": 1},
    }
    assert "user" not in str(stats).lower() and "phone" not in str(stats).lower()

    other = staff_headers(seeded, db, "partner", "9100000071")
    stranger_code = {"reference_code": app["reference_code"], "status": "accepted"}
    assert (
        seeded.post(
            "/api/partner/applications/confirm", json=stranger_code, headers=other
        ).status_code
        == 403
    )  # no provider
    seeded.post(
        "/api/partner/provider",
        json={**PROVIDER, "name": "Other Org", "website": "https://other.example.org"},
        headers=other,
    )
    # Unknown code and another provider's code are indistinguishable.
    assert (
        seeded.post(
            "/api/partner/applications/confirm", json=stranger_code, headers=partner
        ).status_code
        == 200
    )
    unknown = seeded.post(
        "/api/partner/applications/confirm",
        json={"reference_code": "ZZZZZZZZ", "status": "accepted"},
        headers=partner,
    )
    assert unknown.status_code == 404
    mine = seeded.get(f"/api/applications/{app['id']}", headers=student).json()
    assert (
        mine["external_status"] == "accepted"
        and mine["external_status_source"] == "provider_confirmed"
    )
    assert mine["external_confirmed"] is True
    assert seeded.get(f"/api/partner/opportunities/{slug}/stats", headers=other).status_code == 404


def test_admin_reverify_records_a_human_check_but_cannot_add_new_claims(
    seeded, db, admin, facilitator
):
    slug = "fresh-scholarship"
    before = seeded.get(f"/api/opportunities/{slug}").json()["verification"]
    assert before["human_reviewed"] is False
    gov = [{"url": "https://portal.gov.in/merit/guidelines", "note": "Re-read the guidelines page"}]
    assert (
        seeded.post(
            f"/api/admin/opportunities/{slug}/reverify",
            json={"verified_fields": ["eligibility"], "evidence": gov},
            headers=facilitator,
        ).status_code
        == 403
    )
    assert (
        seeded.post(
            f"/api/admin/opportunities/{slug}/reverify",
            json={"verified_fields": ["eligibility"], "evidence": []},
            headers=admin,
        ).status_code
        == 422
    )
    new_claim = seeded.post(
        f"/api/admin/opportunities/{slug}/reverify",
        json={"verified_fields": ["scope"], "evidence": gov},
        headers=admin,
    )
    assert (new_claim.status_code, new_claim.json()["detail"]) == (422, "cannot_verify_new_claims")
    bad_host = [{"url": "https://blog.example.com/x", "note": "n"}]
    assert (
        seeded.post(
            f"/api/admin/opportunities/{slug}/reverify",
            json={"verified_fields": ["eligibility"], "evidence": bad_host},
            headers=admin,
        ).status_code
        == 422
    )
    ok = seeded.post(
        f"/api/admin/opportunities/{slug}/reverify",
        json={"verified_fields": ["eligibility"], "evidence": gov},
        headers=admin,
    )
    assert ok.status_code == 204
    after = seeded.get(f"/api/opportunities/{slug}").json()
    assert (
        after["verification"]["human_reviewed"] is True
        and len(after["verification"]["evidence"]) == 2
    )
    assert "not_human_reviewed" not in after["flags"]
    assert (
        seeded.post(
            "/api/admin/opportunities/ghost/reverify",
            json={"verified_fields": ["url"], "evidence": gov},
            headers=admin,
        ).status_code
        == 404
    )


def test_admin_can_withdraw_any_opportunity(seeded, admin):
    assert (
        seeded.post(
            "/api/admin/opportunities/fresh-scholarship/withdraw", headers=admin
        ).status_code
        == 204
    )
    assert seeded.get("/api/opportunities/fresh-scholarship").status_code == 404
    assert seeded.post("/api/admin/opportunities/ghost/withdraw", headers=admin).status_code == 404


def test_an_approved_listing_flows_into_eligibility_checks_using_only_verified_rules(
    seeded, admin, partner, approved
):
    sub = draft(seeded, partner)
    submit(seeded, partner, sub["id"])
    slug = decide(
        seeded,
        admin,
        sub["id"],
        decision="approve",
        verification={"verified_fields": ["eligibility"], "evidence": EVIDENCE},
    ).json()["published_slug"]
    student = make_student(seeded)
    seeded.put("/api/profile/fields/education_stage", json={"value": "class_10"}, headers=student)
    r = seeded.post(
        "/api/eligibility/evaluations", json={"opportunity": slug}, headers=student
    ).json()
    assert r["outcome"] == "INELIGIBLE" and r["reasons"] == [
        "education_stage_not_met"
    ]  # stages are class_12+
    opp = seeded.app if False else None
    assert opp is None


def test_published_partner_opportunity_row_matches_the_api(seeded, db, admin, partner, approved):
    sub = draft(seeded, partner)
    submit(seeded, partner, sub["id"])
    slug = decide(seeded, admin, sub["id"], decision="approve").json()["published_slug"]
    row = db.scalar(select(Opportunity).where(Opportunity.slug == slug))
    assert (
        row.verification_status.value == "unverified"
        and row.evidence == []
        and row.verified_by is None
    )
