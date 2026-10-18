import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.profile import service
from app.modules.profile.models import ProfileEntry, Provenance, Verification
from tests.conftest import register


@pytest.fixture
def student_id(client_with_db):
    return register(client_with_db).json()["user"]["id"]


def record(db, user_id, provenance, value="class_10", **kw):
    return service.record_entry(
        db,
        user_id=uuid.UUID(str(user_id)),
        key=kw.pop("key", "education_stage"),
        value=value,
        provenance=provenance,
        source=kw.pop("source", "test"),
        recorded_by=None,
        **kw,
    )


def view_field(db, user_id, key="education_stage"):
    entries = service.current_entries(db, uuid.UUID(str(user_id)))
    return next(f for f in service.build_view(entries) if f["key"] == key)


def test_observation_never_overwrites_reported_and_conflict_is_visible(db, student_id):
    record(db, student_id, Provenance.REPORTED, "class_10")
    record(
        db,
        student_id,
        Provenance.OBSERVED,
        "class_9",
        basis="Marksheet seen by facilitator",
        verification=Verification.VERIFIED,
    )
    f = view_field(db, student_id)
    assert {e.provenance for e in f["entries"]} == {Provenance.REPORTED, Provenance.OBSERVED}
    assert f["conflict"] is True


def test_student_correction_does_not_erase_observation(db, student_id):
    record(db, student_id, Provenance.OBSERVED, "class_10", basis="Seen in class")
    record(db, student_id, Provenance.REPORTED, "class_11")
    record(db, student_id, Provenance.REPORTED, "class_12")
    f = view_field(db, student_id)
    by_prov = {e.provenance: e.value for e in f["entries"]}
    assert by_prov == {Provenance.OBSERVED: "class_10", Provenance.REPORTED: "class_12"}


@pytest.mark.parametrize("provenance", [Provenance.OBSERVED, Provenance.HYPOTHESIS])
def test_observed_and_hypothesis_require_a_basis(db, student_id, provenance):
    with pytest.raises(service.InvalidValue):
        record(db, student_id, provenance, ["welding"], key="skills")
    with pytest.raises(service.InvalidValue):
        record(db, student_id, provenance, ["welding"], key="skills", basis="   ")


def test_hypothesis_alone_is_not_established(db, student_id):
    record(db, student_id, Provenance.HYPOTHESIS, ["welding"], key="skills", basis="Likes tools")
    f = view_field(db, student_id, "skills")
    assert f["state"] == "hypothesis_only"
    assert f["conflict"] is False


def test_unknown_entry_cannot_carry_a_value_and_other_entries_need_one(db, student_id):
    with pytest.raises(service.InvalidValue):
        record(db, student_id, Provenance.UNKNOWN, "class_10")
    with pytest.raises(service.InvalidValue):
        record(db, student_id, Provenance.REPORTED, None)


def test_unknown_key_and_invalid_value_are_rejected(db, student_id):
    with pytest.raises(service.UnknownField):
        record(db, student_id, Provenance.REPORTED, "x", key="blood_group")
    with pytest.raises(service.InvalidValue):
        record(db, student_id, Provenance.REPORTED, "phd")


def test_database_allows_only_one_current_entry_per_slot(db, student_id):
    first = record(db, student_id, Provenance.REPORTED, "class_10")
    duplicate = ProfileEntry(
        user_id=first.user_id,
        key=first.key,
        slot=first.slot,
        provenance=Provenance.REPORTED,
        value="class_11",
        source="test",
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
