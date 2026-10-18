"""Demo data for the hackathon prototype: `python -m app.admin.demo`.

Creates clearly labelled DEMO accounts (all with publicly documented, throw-away credentials)
so the whole journey can be shown without typing anything first. Safe to run repeatedly.
NEVER run this against a real deployment: the PINs are public.
"""

import sys
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import make_engine, make_session_factory
from app.modules.facilitator.models import FacilitatorAssignment
from app.modules.identity import service as identity
from app.modules.identity.models import Role, User
from app.modules.identity.schemas import ConsentRequest, RegisterRequest
from app.modules.profile import service as profile
from app.modules.profile.models import Provenance

STAFF_PIN = "12345678"
STUDENT_PIN = "1234"

STAFF = [
    ("admin", "9000000001", "DEMO Admin"),
    ("facilitator", "9000000002", "DEMO Teacher Meena"),
    ("partner", "9000000003", "DEMO Partner"),
]
# (phone, name, date of birth, language, profile)
STUDENTS = [
    (
        "9000000011",
        "DEMO Asha (age 15)",
        date(date.today().year - 15, 3, 14),
        "ta",
        {
            "education_stage": "class_10",
            "interests": ["விவசாயம்", "fixing bikes"],
            "skills": ["stitching"],
            "state": "Tamil Nadu",
            "district": "Thanjavur",
            "weekly_learning_hours": 6,
        },
    ),
    (
        "9000000012",
        "DEMO Karthik (age 20)",
        date(date.today().year - 20, 8, 2),
        "en",
        {},  # a fresh student: starts the interview from scratch
    ),
]


def ensure_staff(db: Session) -> dict[str, User]:
    out: dict[str, User] = {}
    for role, phone, name in STAFF:
        user = db.scalar(select(User).where(User.phone == phone))
        if user is None:
            user = identity.create_staff_user(db, Role(role), phone, STAFF_PIN, name, None)
        out[role] = user
    return out


def ensure_student(db: Session, phone: str, name: str, dob: date, lang: str, data: dict) -> User:
    user = db.scalar(select(User).where(User.phone == phone))
    if user is not None:
        return user
    user = identity.register_student(
        db,
        RegisterRequest(
            display_name=name,
            phone=phone,
            pin=STUDENT_PIN,
            date_of_birth=dob,
            preferred_language=lang,
        ),
    )
    minor = identity.is_minor(user)
    consent = (
        ConsentRequest(
            given_by="guardian", guardian_name="DEMO Parent", guardian_phone="9000000099"
        )
        if minor
        else ConsentRequest(given_by="self")
    )
    identity.grant_consent(db, user, consent)
    for key, value in data.items():
        profile.record_entry(
            db,
            user_id=user.id,
            key=key,
            value=value,
            provenance=Provenance.REPORTED,
            source="demo_seed",
            recorded_by=user.id,
        )
    return user


def main() -> int:
    with make_session_factory(make_engine(get_settings()))() as db:
        staff = ensure_staff(db)
        students = [ensure_student(db, *s) for s in STUDENTS]
        asha = students[0]
        # Asha has agreed to share her profile with her teacher; Karthik has not (to show the gate).
        if not identity.has_valid_consent(db, asha, identity.FACILITATOR_ACCESS):
            identity.grant_consent(
                db,
                asha,
                ConsentRequest(
                    given_by="guardian", guardian_name="DEMO Parent", guardian_phone="9000000099"
                ),
                identity.FACILITATOR_ACCESS,
            )
        for student in students:
            exists = db.scalar(
                select(FacilitatorAssignment).where(
                    FacilitatorAssignment.facilitator_id == staff["facilitator"].id,
                    FacilitatorAssignment.student_id == student.id,
                    FacilitatorAssignment.ended_at.is_(None),
                )
            )
            if exists is None:
                db.add(
                    FacilitatorAssignment(
                        facilitator_id=staff["facilitator"].id,
                        student_id=student.id,
                        assigned_by=staff["admin"].id,
                    )
                )
        db.commit()
    print("Demo accounts ready (throw-away credentials, never use in production):")
    print(f"  admin        9000000001  PIN {STAFF_PIN}")
    print(f"  facilitator  9000000002  PIN {STAFF_PIN}")
    print(f"  partner      9000000003  PIN {STAFF_PIN}")
    print(f"  student Asha (15, Tamil, filled profile)  9000000011  PIN {STUDENT_PIN}")
    print(f"  student Karthik (20, English, empty)      9000000012  PIN {STUDENT_PIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
