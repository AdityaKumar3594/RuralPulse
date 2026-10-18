import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.config import Settings
from app.core.security import hash_pin, verify_pin
from app.modules.identity.models import Consent, ConsentGivenBy, Role, User
from app.modules.identity.schemas import ConsentRequest, RegisterRequest

DATA_PROCESSING = "data_processing"
# Student (or guardian) agrees that assigned facilitators may see and help with their profile.
FACILITATOR_ACCESS = "facilitator_access"
# Version of the consent notice shown to users. The notice text still needs legal review.
CONSENT_POLICY_VERSION = "draft-2026-10"
ADULT_AGE = 18
MIN_STUDENT_AGE = 10
MAX_STUDENT_AGE = 80


class IdentityError(Exception):
    """Base for expected, user-facing identity errors."""


class PhoneAlreadyRegistered(IdentityError):
    pass


class InvalidDateOfBirth(IdentityError):
    pass


class InvalidCredentials(IdentityError):
    pass


class AccountLocked(IdentityError):
    pass


class ConsentNotAllowed(IdentityError):
    pass


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def is_minor(user: User, today: date | None = None) -> bool:
    """Users with no date of birth are treated as minors (the safe default)."""
    if user.date_of_birth is None:
        return True
    return age_on(user.date_of_birth, today or datetime.now(UTC).date()) < ADULT_AGE


def register_student(db: Session, data: RegisterRequest) -> User:
    age = age_on(data.date_of_birth, datetime.now(UTC).date())
    if not MIN_STUDENT_AGE <= age <= MAX_STUDENT_AGE:
        raise InvalidDateOfBirth
    user = User(
        role=Role.STUDENT,
        phone=data.phone,
        pin_hash=hash_pin(data.pin),
        display_name=data.display_name,
        date_of_birth=data.date_of_birth,
        preferred_language=data.preferred_language,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise PhoneAlreadyRegistered from None
    audit(db, "user.registered", actor_id=user.id, subject_user_id=user.id)
    db.commit()
    return user


def authenticate(db: Session, settings: Settings, phone: str, pin: str) -> User:
    """Check phone + PIN. Unknown phone and wrong PIN look the same; repeated failures lock."""
    now = datetime.now(UTC)
    user = db.scalar(select(User).where(User.phone == phone))
    if user is not None and user.locked_until and user.locked_until > now:
        raise AccountLocked
    ok = verify_pin(pin, user.pin_hash if user else None)
    if user is None or not user.is_active or not ok:
        if user is not None:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.max_failed_logins:
                user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
                user.failed_login_attempts = 0
                audit(db, "user.locked", actor_id=None, subject_user_id=user.id)
            db.commit()
        raise InvalidCredentials
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return user


def get_user(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def required_consent_giver(user: User) -> ConsentGivenBy:
    return ConsentGivenBy.GUARDIAN if is_minor(user) else ConsentGivenBy.SELF


def get_active_consent(
    db: Session, user_id: uuid.UUID, purpose: str = DATA_PROCESSING
) -> Consent | None:
    return db.scalar(
        select(Consent).where(
            Consent.user_id == user_id,
            Consent.purpose == purpose,
            Consent.withdrawn_at.is_(None),
        )
    )


def has_valid_consent(db: Session, user: User, purpose: str = DATA_PROCESSING) -> bool:
    consent = get_active_consent(db, user.id, purpose)
    return consent is not None and consent.given_by == required_consent_giver(user)


def grant_consent(
    db: Session, user: User, data: ConsentRequest, purpose: str = DATA_PROCESSING
) -> Consent:
    given_by = ConsentGivenBy(data.given_by)
    if given_by != required_consent_giver(user):
        raise ConsentNotAllowed
    existing = get_active_consent(db, user.id, purpose)
    if existing is not None:
        existing.withdrawn_at = datetime.now(UTC)  # replaced by the new record
        db.flush()
    consent = Consent(
        user_id=user.id,
        purpose=purpose,
        policy_version=CONSENT_POLICY_VERSION,
        given_by=given_by,
        guardian_name=data.guardian_name,
        guardian_phone=data.guardian_phone,
    )
    db.add(consent)
    audit(
        db,
        "consent.granted",
        actor_id=user.id,
        subject_user_id=user.id,
        given_by=given_by.value,
        purpose=purpose,
    )
    db.commit()
    return consent


def withdraw_consent(db: Session, user: User, purpose: str = DATA_PROCESSING) -> bool:
    consent = get_active_consent(db, user.id, purpose)
    if consent is None:
        return False
    consent.withdrawn_at = datetime.now(UTC)
    audit(db, "consent.withdrawn", actor_id=user.id, subject_user_id=user.id, purpose=purpose)
    db.commit()
    return True


STAFF_ROLES = (Role.FACILITATOR, Role.PARTNER, Role.ADMIN)


class WeakStaffPin(IdentityError):
    pass


def create_staff_user(
    db: Session,
    role: Role,
    phone: str,
    pin: str,
    display_name: str,
    created_by: uuid.UUID | None,
) -> User:
    """Staff accounts are never self-service. Their PIN must be 6 to 12 digits."""
    if role not in STAFF_ROLES:
        raise ValueError("not a staff role")
    if not (pin.isdigit() and 6 <= len(pin) <= 12):
        raise WeakStaffPin
    user = User(
        role=role,
        phone=phone,
        pin_hash=hash_pin(pin),
        display_name=display_name,
        preferred_language="ta",
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise PhoneAlreadyRegistered from None
    audit(
        db,
        "user.staff_created",
        actor_id=created_by,
        subject_user_id=user.id,
        role=role.value,
    )
    db.commit()
    return user
