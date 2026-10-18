import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, model_validator


class ExplainRequest(BaseModel):
    kind: Literal["recommendation", "eligibility", "pathway"]
    language: Literal["ta", "en"] = "en"
    run_id: uuid.UUID | None = None  # recommendation
    career: str | None = None  # recommendation
    evaluation_id: uuid.UUID | None = None  # eligibility
    plan_id: uuid.UUID | None = None  # pathway

    @model_validator(mode="after")
    def _needs_ref(self) -> "ExplainRequest":
        needed = {
            "recommendation": (self.run_id, self.career),
            "eligibility": (self.evaluation_id,),
            "pathway": (self.plan_id,),
        }[self.kind]
        if not all(needed):
            raise ValueError(f"missing reference for kind={self.kind}")
        return self

    def ref(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "career": self.career,
            "evaluation_id": self.evaluation_id,
            "plan_id": self.plan_id,
        }


class ExplanationFields(BaseModel):
    headline: str
    why: list[str]
    requirements: list[str]
    # Computed by the rules engine; an explanation can never change it.
    eligibility_status: Literal[
        "ELIGIBLE", "INELIGIBLE", "UNKNOWN", "NEEDS_REVIEW", "NOT_APPLICABLE"
    ]
    freshness_note: str
    missing_information: list[str]
    next_action: str


class ExplanationOut(BaseModel):
    id: uuid.UUID
    kind: str
    language: str
    source: Literal["ai", "template"]
    fallback_reason: str | None  # why the template was used, when it was
    model: str | None
    cached: bool
    explanation: ExplanationFields
    sources: list[dict[str, Any]]
    created_at: datetime
