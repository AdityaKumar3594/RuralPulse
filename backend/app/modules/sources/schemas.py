from datetime import date
from typing import Any, Literal

from pydantic import BaseModel


class SourceBrief(BaseModel):
    id: str
    name: str
    publisher: str
    base_url: str


class SourceOut(SourceBrief):
    category: str
    api_access: str
    notes: str | None


class VerificationOut(BaseModel):
    status: Literal["unverified", "verified"]
    verified_fields: list[str]
    verified_at: date | None
    verified_by: str | None
    human_reviewed: bool
    evidence: list[dict[str, str]]


class BenefitOut(BaseModel):
    text: str | None
    amount_inr: int | None
    period: str | None


class OpportunityBrief(BaseModel):
    slug: str
    kind: str
    title: str | None
    url: str


class OpportunityOut(OpportunityBrief):
    summary: str | None
    provider: str
    source: SourceBrief
    scope: dict[str, Any]
    eligibility: dict[str, Any] | None
    required_documents: list[str]
    application_deadline: date | None
    expires_on: date | None
    benefits: list[BenefitOut]
    verification: VerificationOut
    freshness: Literal["fresh", "stale", "expired", "unverified"]
    flags: list[str]
    language: str
    language_fallback: bool
