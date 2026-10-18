import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.modules.profile.fields import FIELDS
from app.modules.profile.models import ProfileEntry, Provenance, Slot, Verification

_SLOT_FOR = {
    Provenance.REPORTED: Slot.SELF,
    Provenance.UNKNOWN: Slot.SELF,
    Provenance.OBSERVED: Slot.OBSERVED,
    Provenance.HYPOTHESIS: Slot.HYPOTHESIS,
}


class ProfileError(Exception):
    pass


class UnknownField(ProfileError):
    pass


class InvalidValue(ProfileError):
    pass


def record_entry(
    db: Session,
    *,
    user_id: uuid.UUID,
    key: str,
    value: Any,
    provenance: Provenance,
    source: str,
    recorded_by: uuid.UUID | None,
    basis: str | None = None,
    verification: Verification = Verification.UNVERIFIED,
    commit: bool = True,
) -> ProfileEntry:
    """Validate and store one entry, superseding the current entry in the same slot.

    Pass commit=False to make this part of a larger transaction (the caller commits).

    Observed and hypothesis entries live in their own slots, so they never overwrite what the
    student reported (and a student's correction never erases an observation).
    """
    spec = FIELDS.get(key)
    if spec is None:
        raise UnknownField(key)
    if provenance is Provenance.UNKNOWN:
        if value is not None:
            raise InvalidValue("an 'unknown' entry cannot carry a value")
        stored = None
    else:
        if value is None:
            raise InvalidValue("value is required")
        try:
            stored = spec.validate(value)
        except ValidationError as exc:
            raise InvalidValue(f"invalid value for {key}") from exc
    if provenance in (Provenance.OBSERVED, Provenance.HYPOTHESIS) and not (basis and basis.strip()):
        raise InvalidValue(f"{provenance.value} entries require a basis")

    slot = _SLOT_FOR[provenance]
    now = datetime.now(UTC)
    current = db.scalar(
        select(ProfileEntry).where(
            ProfileEntry.user_id == user_id,
            ProfileEntry.key == key,
            ProfileEntry.slot == slot,
            ProfileEntry.superseded_at.is_(None),
        )
    )
    if current is not None:
        current.superseded_at = now
        db.flush()  # free the unique "current slot" index before inserting the replacement
    entry = ProfileEntry(
        user_id=user_id,
        key=key,
        slot=slot,
        provenance=provenance,
        value=stored,
        verification=verification,
        source=source,
        basis=basis,
        recorded_by=recorded_by,
        created_at=now,
    )
    db.add(entry)
    # Audit the key only; profile values are personal data and stay out of the log.
    audit(
        db,
        "profile.entry_recorded",
        actor_id=recorded_by,
        subject_user_id=user_id,
        key=key,
        provenance=provenance.value,
    )
    if commit:
        db.commit()
    else:
        db.flush()
    return entry


def current_entries(db: Session, user_id: uuid.UUID) -> list[ProfileEntry]:
    return list(
        db.scalars(
            select(ProfileEntry)
            .where(ProfileEntry.user_id == user_id, ProfileEntry.superseded_at.is_(None))
            .order_by(ProfileEntry.created_at)
        )
    )


def build_view(entries: list[ProfileEntry]) -> list[dict[str, Any]]:
    """One item per registry field. `state` never treats missing evidence as inability."""
    by_key: dict[str, list[ProfileEntry]] = {}
    for e in entries:
        by_key.setdefault(e.key, []).append(e)
    view = []
    for key, spec in FIELDS.items():
        items = by_key.get(key, [])
        reported = next((e for e in items if e.provenance is Provenance.REPORTED), None)
        observed = next((e for e in items if e.provenance is Provenance.OBSERVED), None)
        if reported or observed:
            state = "established"
        elif any(e.provenance is Provenance.HYPOTHESIS for e in items):
            state = "hypothesis_only"
        else:
            state = "unknown"
        view.append(
            {
                "key": key,
                "description": spec.description,
                "state": state,
                "conflict": bool(reported and observed and reported.value != observed.value),
                "entries": items,
            }
        )
    return view
