import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CreatePlanRequest(BaseModel):
    career: str = Field(max_length=60)
    language: Literal["ta", "en"] = "en"
    refresh: bool = False


class ProgressUpdate(BaseModel):
    status: Literal["not_started", "in_progress", "done"]
    note: str | None = Field(default=None, max_length=500)


class StepOut(BaseModel):
    id: str
    type: str
    group: str
    title: str | None
    depends_on: list[str]
    # typical_route | suggested_preparation. Nothing is "mandatory": no verified official source.
    requirement_level: str
    estimated_effort: None = None  # no effort data exists, so it is never estimated
    stage: str | None
    route_index: int | None
    route_kind: str | None = None
    skills: list[str] | None
    resource: dict[str, Any] | None
    completion_criteria: dict[str, Any]
    status: Literal["not_started", "in_progress", "done"]
    note: str | None


class PlanOut(BaseModel):
    id: uuid.UUID
    career: dict[str, Any]
    version: str
    student_stage: str | None
    created_at: datetime
    steps: list[StepOut]
    alternatives: list[str]
    unknowns: list[str]
    language_fallback: bool
