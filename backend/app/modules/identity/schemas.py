import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Phone = Annotated[str, StringConstraints(pattern=r"^[6-9]\d{9}$")]  # Indian mobile, no country code
Pin = Annotated[str, StringConstraints(pattern=r"^\d{4,6}$")]  # students
LoginPin = Annotated[str, StringConstraints(pattern=r"^\d{4,12}$")]  # staff PINs are longer
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class RegisterRequest(BaseModel):
    display_name: Name
    phone: Phone
    pin: Pin
    date_of_birth: date
    preferred_language: Literal["ta", "en"] = "ta"


class LoginRequest(BaseModel):
    phone: Phone
    pin: LoginPin


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    display_name: str
    preferred_language: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - not a secret
    user: UserOut


class ConsentRequest(BaseModel):
    given_by: Literal["self", "guardian"]
    guardian_name: Name | None = None
    guardian_phone: Phone | None = None

    @model_validator(mode="after")
    def _guardian_details(self) -> "ConsentRequest":
        if self.given_by == "guardian" and not (self.guardian_name and self.guardian_phone):
            raise ValueError("guardian_name and guardian_phone are required for guardian consent")
        if self.given_by == "self" and (self.guardian_name or self.guardian_phone):
            raise ValueError("guardian details must not be sent with self consent")
        return self


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    purpose: str
    policy_version: str
    given_by: str
    verification: str
    granted_at: datetime


class ConsentStatus(BaseModel):
    required_given_by: Literal["self", "guardian"]
    policy_version: str
    active: ConsentOut | None = Field(description="Current consent, or null if none/withdrawn")
