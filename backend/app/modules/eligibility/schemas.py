import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.modules.sources.schemas import OpportunityBrief


class EvaluateRequest(BaseModel):
    opportunity: str
    language: Literal["ta", "en"] = "en"


class CheckOut(BaseModel):
    rule: str
    result: Literal["pass", "fail", "unknown", "conflict"]
    expected: Any = None
    actual: Any = None
    basis: str | None = None


class MissingFact(BaseModel):
    fact: str
    question_id: str | None  # interview question that collects it; null = set at registration


class EvaluationOut(BaseModel):
    id: uuid.UUID
    opportunity: OpportunityBrief
    outcome: Literal["ELIGIBLE", "INELIGIBLE", "UNKNOWN", "NEEDS_REVIEW"]
    reasons: list[str]
    checks: list[CheckOut]
    missing: list[MissingFact]
    flags: list[str]
    facts_used: dict[str, Any]
    rules_version: str
    opportunity_fingerprint: str
    record: dict[str, Any]
    evaluated_on: date
    evaluated_at: datetime
