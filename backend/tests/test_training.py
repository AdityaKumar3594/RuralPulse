import pytest

from tests.conftest import make_student, staff_headers

LESSONS = [
    {"title": "Welcome", "body": "What we will learn."},
    {"title": "Soil basics", "body": "Types of soil.", "url": "https://example.org/soil"},
]


def module_body(**over):
    return {
        "title": "Kitchen gardens",
        "description": "Grow vegetables at home.",
        "language": "ta",
        "lessons": LESSONS,
        **over,
    }


def create(client, headers, **over):
    r = client.post("/api/facilitator/modules", json=module_body(**over), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def publish(client, headers, mid):
    r = client.post(f"/api/facilitator/modules/{mid}/publish", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_only_facilitators_author_modules(seeded, admin, partner):
    student = make_student(seeded)
    for headers in (student, admin, partner):
        assert (
            seeded.post("/api/facilitator/modules", json=module_body(), headers=headers).status_code
            == 403
        )


def test_pricing_rules(seeded, facilitator):
    assert (
        seeded.post(
            "/api/facilitator/modules",
            json=module_body(price_type="per_module"),
            headers=facilitator,
        ).status_code
        == 409
    )
    assert (
        seeded.post(
            "/api/facilitator/modules",
            json=module_body(price_type="free", price_inr=50),
            headers=facilitator,
        ).status_code
        == 409
    )
    assert (
        seeded.post(
            "/api/facilitator/modules",
            json=module_body(price_type="subscription", price_inr=0),
            headers=facilitator,
        ).status_code
        == 422
    )
    paid = create(seeded, facilitator, price_type="per_module", price_inr=99)
    assert paid["price_inr"] == 99 and paid["status"] == "draft" and paid["lessons"] is not None
    back = seeded.put(
        f"/api/facilitator/modules/{paid['id']}", json={"price_type": "free"}, headers=facilitator
    ).json()
    assert back["price_type"] == "free" and back["price_inr"] is None


def test_publishing_needs_a_lesson_and_only_the_owner_can_manage(seeded, db, facilitator):
    empty = create(seeded, facilitator, lessons=[])
    r = seeded.post(f"/api/facilitator/modules/{empty['id']}/publish", headers=facilitator)
    assert (r.status_code, r.json()["detail"]) == (409, "needs_at_least_one_lesson")
    seeded.put(
        f"/api/facilitator/modules/{empty['id']}", json={"lessons": LESSONS}, headers=facilitator
    )
    assert publish(seeded, facilitator, empty["id"])["status"] == "published"
    other = staff_headers(seeded, db, "facilitator", "9100000080")
    assert (
        seeded.put(
            f"/api/facilitator/modules/{empty['id']}", json={"title": "Hijacked"}, headers=other
        ).status_code
        == 404
    )
    assert (
        seeded.post(f"/api/facilitator/modules/{empty['id']}/withdraw", headers=other).status_code
        == 404
    )
    assert seeded.get("/api/facilitator/modules", headers=other).json() == []


def test_students_see_only_published_modules_and_lessons_are_locked_until_enrolled(
    seeded, facilitator
):
    student = make_student(seeded)
    draft = create(seeded, facilitator)
    assert seeded.get("/api/modules", headers=student).json() == []
    assert seeded.get(f"/api/modules/{draft['id']}", headers=student).status_code == 404
    publish(seeded, facilitator, draft["id"])
    [listed] = seeded.get("/api/modules", headers=student).json()
    assert (
        listed["lesson_titles"] == ["Welcome", "Soil basics"]
        and listed["lessons"] is None
        and listed["access"] is False
    )
    enrolled = seeded.post(f"/api/modules/{draft['id']}/enroll", headers=student)
    assert enrolled.status_code == 201 and enrolled.json()["access"] is True
    assert enrolled.json()["lessons"][0]["body"] == "What we will learn."
    assert (
        seeded.post(f"/api/modules/{draft['id']}/enroll", headers=student).status_code == 200
    )  # idempotent


def test_lesson_progress_is_tracked_and_bounded(seeded, facilitator):
    student = make_student(seeded)
    m = publish(seeded, facilitator, create(seeded, facilitator)["id"])
    seeded.post(f"/api/modules/{m['id']}/enroll", headers=student)
    r = seeded.put(f"/api/modules/{m['id']}/lessons/1", json={"done": True}, headers=student)
    assert r.json()["completed_lessons"] == [1]
    seeded.put(f"/api/modules/{m['id']}/lessons/0", json={}, headers=student)
    assert seeded.get(f"/api/modules/{m['id']}", headers=student).json()["completed_lessons"] == [
        0,
        1,
    ]
    assert seeded.put(
        f"/api/modules/{m['id']}/lessons/1", json={"done": False}, headers=student
    ).json()["completed_lessons"] == [0]
    assert (
        seeded.put(f"/api/modules/{m['id']}/lessons/5", json={}, headers=student).status_code == 404
    )
    other = make_student(seeded, phone="9200000009")
    assert (
        seeded.put(f"/api/modules/{m['id']}/lessons/0", json={}, headers=other).status_code == 404
    )  # not enrolled


@pytest.mark.parametrize("price_type", ["per_module", "subscription"])
def test_paid_modules_can_be_reserved_but_never_unlocked_because_there_is_no_payment_gateway(
    seeded, facilitator, price_type
):
    student = make_student(seeded)
    m = publish(
        seeded, facilitator, create(seeded, facilitator, price_type=price_type, price_inr=99)["id"]
    )
    r = seeded.post(f"/api/modules/{m['id']}/enroll", headers=student).json()
    assert r["payment_status"] == "unpaid_no_gateway" and r["access"] is False
    assert r["lessons"] is None and r["payments_available"] is False
    blocked = seeded.put(f"/api/modules/{m['id']}/lessons/0", json={}, headers=student)
    assert (blocked.status_code, blocked.json()["detail"]) == (409, "payment_not_available")


def test_facilitators_see_enrolment_counts_and_can_withdraw(seeded, facilitator):
    m = publish(seeded, facilitator, create(seeded, facilitator)["id"])
    for i in range(2):
        seeded.post(
            f"/api/modules/{m['id']}/enroll", headers=make_student(seeded, phone=f"920000010{i}")
        )
    [mine] = seeded.get("/api/facilitator/modules", headers=facilitator).json()
    assert mine["enrollments"] == 2 and mine["module"]["lessons"] is not None
    seeded.post(f"/api/facilitator/modules/{m['id']}/withdraw", headers=facilitator)
    student = make_student(seeded, phone="9200000200")
    assert seeded.get("/api/modules", headers=student).json() == []
    assert seeded.post(f"/api/modules/{m['id']}/enroll", headers=student).status_code == 404


def test_lesson_links_must_be_https_and_sizes_are_bounded(seeded, facilitator):
    bad_link = [{"title": "x", "body": "y", "url": "http://insecure.example.org"}]
    assert (
        seeded.post(
            "/api/facilitator/modules", json=module_body(lessons=bad_link), headers=facilitator
        ).status_code
        == 422
    )
    assert (
        seeded.post(
            "/api/facilitator/modules",
            json=module_body(lessons=[{"title": "x", "body": "y" * 4001}]),
            headers=facilitator,
        ).status_code
        == 422
    )
    assert (
        seeded.post(
            "/api/facilitator/modules",
            json=module_body(lessons=[LESSONS[0]] * 31),
            headers=facilitator,
        ).status_code
        == 422
    )
