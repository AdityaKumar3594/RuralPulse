from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_access_token
from app.modules.identity import service
from app.modules.identity.deps import (
    get_current_user,
    require_student,
    require_student_with_consent,
)
from app.modules.identity.models import User
from app.modules.identity.schemas import (
    ConsentOut,
    ConsentRequest,
    ConsentStatus,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(tags=["identity"])


def _token_response(request: Request, user: User) -> TokenResponse:
    token = create_access_token(request.app.state.settings, user.id, user.role.value)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    try:
        user = service.register_student(db, data)
    except service.PhoneAlreadyRegistered:
        raise HTTPException(status.HTTP_409_CONFLICT, "phone_already_registered") from None
    except service.InvalidDateOfBirth:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_date_of_birth"
        ) from None
    return _token_response(request, user)


@router.post("/auth/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    try:
        user = service.authenticate(db, request.app.state.settings, data.phone, data.pin)
    except service.AccountLocked:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "account_locked") from None
    except service.InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials") from None
    return _token_response(request, user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/consents/me", response_model=ConsentStatus)
def consent_status(user: User = Depends(require_student), db: Session = Depends(get_db)):
    return ConsentStatus(
        required_given_by=service.required_consent_giver(user).value,
        policy_version=service.CONSENT_POLICY_VERSION,
        active=service.get_active_consent(db, user.id),
    )


@router.post("/consents", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
def grant_consent(
    data: ConsentRequest,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    try:
        return service.grant_consent(db, user, data)
    except service.ConsentNotAllowed:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "wrong_consent_giver") from None


@router.post("/consents/withdraw", status_code=status.HTTP_204_NO_CONTENT)
def withdraw_consent(user: User = Depends(require_student), db: Session = Depends(get_db)):
    service.withdraw_consent(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/consents/facilitator-access", response_model=ConsentStatus)
def facilitator_access_status(user: User = Depends(require_student), db: Session = Depends(get_db)):
    """Whether the student agreed that assigned facilitators may see and help with their profile."""
    return ConsentStatus(
        required_given_by=service.required_consent_giver(user).value,
        policy_version=service.CONSENT_POLICY_VERSION,
        active=service.get_active_consent(db, user.id, service.FACILITATOR_ACCESS),
    )


@router.post(
    "/consents/facilitator-access", response_model=ConsentOut, status_code=status.HTTP_201_CREATED
)
def grant_facilitator_access(
    data: ConsentRequest,
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    try:
        return service.grant_consent(db, user, data, service.FACILITATOR_ACCESS)
    except service.ConsentNotAllowed:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "wrong_consent_giver") from None


@router.post("/consents/facilitator-access/withdraw", status_code=status.HTTP_204_NO_CONTENT)
def withdraw_facilitator_access(
    user: User = Depends(require_student), db: Session = Depends(get_db)
):
    service.withdraw_consent(db, user, service.FACILITATOR_ACCESS)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
