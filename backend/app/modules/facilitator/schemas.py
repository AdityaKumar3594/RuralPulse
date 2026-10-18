import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.applications.models import ExternalStatus
from app.modules.facilitator.models import EndorsementStatus, HelpTopic, ReviewDecision


class StudentSummary(BaseModel):
    id: uuid.UUID
    display_name: str
    preferred_language: str
    is_minor: bool
    shared: bool
    open_help_requests: int


class StudentProfileOut(BaseModel):
    student: StudentSummary
    fields: list[dict[str, Any]]


class ObservationIn(BaseModel):
    """What the facilitator saw, with the basis for it. Never overwrites what the student said."""

    key: str = Field(max_length=50)
    value: Any
    provenance: Literal["observed", "hypothesis"] = "observed"
    basis: str = Field(min_length=3, max_length=500)
    verified: bool = False  # the facilitator saw proof (e.g. a marksheet), not just an impression


class AssistedAnswerIn(BaseModel):
    """The student told the facilitator this (e.g. during a sit-down interview)."""

    key: str = Field(max_length=50)
    value: Any = None
    unknown: bool = False

    @model_validator(mode="after")
    def _one(self) -> "AssistedAnswerIn":
        if self.unknown == (self.value is not None):
            raise ValueError("send either a value or unknown=true")
        return self


class ReviewIn(BaseModel):
    run_id: uuid.UUID
    career: str = Field(max_length=60)
    decision: ReviewDecision
    note: str | None = Field(default=None, max_length=500)


class EndorseIn(BaseModel):
    opportunity: str = Field(max_length=60)
    note: str | None = Field(default=None, max_length=300)


class EndorsementOut(BaseModel):
    id: uuid.UUID
    opportunity_slug: str
    note: str | None
    status: str
    created_at: datetime


class ConfirmIn(BaseModel):
    status: Literal["submitted", "under_review", "accepted", "rejected"]
    note: str | None = Field(default=None, max_length=300)

    def external(self) -> ExternalStatus:
        return ExternalStatus(self.status)


class HelpRequestIn(BaseModel):
    topic: HelpTopic = HelpTopic.GENERAL
    message: str | None = Field(default=None, max_length=500)


class HelpRequestOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    topic: str
    message: str | None
    opportunity_slug: str | None
    status: str
    created_at: datetime


class EndorsementStatusIn(BaseModel):
    status: Literal["seen", "dismissed"]

    def value(self) -> EndorsementStatus:
        return EndorsementStatus(self.status)


class MyFacilitator(BaseModel):
    id: uuid.UUID
    display_name: str
    since: datetime
