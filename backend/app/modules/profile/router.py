from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identity.deps import require_student_with_consent
from app.modules.identity.models import User
from app.modules.profile import service
from app.modules.profile.models import Provenance
from app.modules.profile.schemas import FieldUpdate, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])


def _view(db: Session, user: User) -> dict[str, Any]:
    return {"fields": service.build_view(service.current_entries(db, user.id))}


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(require_student_with_consent), db: Session = Depends(get_db)):
    return _view(db, user)


@router.put("/fields/{key}", response_model=ProfileOut)
def update_field(
    key: str,
    data: FieldUpdate,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    """Students can only add what they report (or say they don't know); never other provenance."""
    try:
        service.record_entry(
            db,
            user_id=user.id,
            key=key,
            value=data.value,
            provenance=Provenance.UNKNOWN if data.unknown else Provenance.REPORTED,
            source="student_form",
            recorded_by=user.id,
        )
    except service.UnknownField:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_field") from None
    except service.InvalidValue:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_value") from None
    return _view(db, user)
