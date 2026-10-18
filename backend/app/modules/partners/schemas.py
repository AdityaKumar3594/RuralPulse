import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.modules.catalog.seed_schema import Localized, _require_english
from app.modules.partners.models import ProviderKind
from app.modules.sources.seed_schema import (
    Benefit,
    Eligibility,
    OpportunityKind,
    Scope,
    VerifiedField,
)


class ProviderIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    kind: ProviderKind
    website: str = Field(max_length=300)
    description: str | None = Field(default=None, max_length=1000)


class ProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    kind: ProviderKind | None = None
    website: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=1000)


class ProviderOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    website: str
    description: str | None
    status: Literal["pending", "approved", "suspended"]
    created_at: datetime


class SubmissionPayload(BaseModel):
    """What a partner proposes. Everything here is a *claim* until an administrator verifies it."""

    kind: OpportunityKind
    title: Localized
    summary: Localized
    url: str = Field(max_length=300)
    keywords: list[str] = Field(default=[], max_length=20)
    scope: Scope = Scope()
    eligibility: Eligibility | None = None
    required_documents: list[str] = Field(default=[], max_length=15)
    application_deadline: date | None = None
    expires_on: date | None = None
    benefits: list[Benefit] = Field(default=[], max_length=10)

    @field_validator("title", "summary")
    @classmethod
    def _english_required(cls, v: dict) -> dict:
        return _require_english(v)


class SubmissionOut(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    status: str
    payload: dict[str, Any]
    replaces_slug: str | None
    review_notes: str | None
    published_slug: str | None
    revision: int
    created_at: datetime
    updated_at: datetime


class EvidenceIn(BaseModel):
    url: str = Field(max_length=300)
    note: str = Field(max_length=300)


class VerificationIn(BaseModel):
    """What the reviewing administrator has actually checked, with proof."""

    verified_fields: list[VerifiedField] = []
    evidence: list[EvidenceIn] = []


class DecisionIn(BaseModel):
    decision: Literal["approve", "request_changes", "reject"]
    notes: str | None = Field(default=None, max_length=1000)
    verification: VerificationIn = VerificationIn()


class DecisionOut(BaseModel):
    submission: SubmissionOut
    published_slug: str | None
    verification_status: str | None
    stripped_claims: list[str]


class ConfirmIn(BaseModel):
    reference_code: str = Field(min_length=8, max_length=8)
    status: Literal["submitted", "under_review", "accepted", "rejected"]
    note: str | None = Field(default=None, max_length=300)


class ConfirmOut(BaseModel):
    opportunity: str
    external_status: str


class StatsOut(BaseModel):
    opportunity: str
    by_internal_status: dict[str, int]
    by_external_status: dict[str, int]
