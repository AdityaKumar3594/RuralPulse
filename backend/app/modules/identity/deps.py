from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.modules.identity import service
from app.modules.identity.models import Role, User

_bearer = HTTPBearer(auto_error=False)
_UNAUTHENTICATED = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _UNAUTHENTICATED
    user_id = decode_access_token(request.app.state.settings, credentials.credentials)
    user = service.get_user(db, user_id) if user_id else None
    if user is None or not user.is_active:
        raise _UNAUTHENTICATED
    return user


def require_role(*roles: Role) -> Callable[[User], User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed for this role")
        return user

    return dependency


require_student = require_role(Role.STUDENT)


def require_student_with_consent(
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> User:
    """Student endpoints that touch the profile need valid consent (guardian consent for minors)."""
    if not service.has_valid_consent(db, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "consent_required")
    return user
