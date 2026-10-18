import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    language: Literal["ta", "en"] = "en"
    limit: int = Field(default=5, ge=1, le=10)


class ReasonOut(BaseModel):
    student_field: str
    student_term: str
    basis: str
    career_field: str
    matched_text: str
    points: float


class CareerCard(BaseModel):
    slug: str
    family: str
    title: str | None
    description: str | None
    entry_notes: str | None


class RecommendationOut(BaseModel):
    slug: str
    family: str
    kind: Literal["match", "explore"]
    # Keyword-match points. NOT a probability of success or a measure of ability.
    points: float | None
    match_level: Literal["strong", "moderate", "weak"] | None
    reasons: list[ReasonOut]
    stage: dict[str, Any]
    unknowns: list[str]
    career: CareerCard
    routes: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    next_actions: list[dict[str, Any]]
    flags: list[str]
    language_fallback: bool


class MissingProfileItem(BaseModel):
    field: str
    question_id: str | None


class RunOut(BaseModel):
    id: uuid.UUID
    ranking_version: str
    status: Literal["ok", "no_matches", "insufficient_profile"]
    created_at: datetime
    families: list[str]
    profile_summary: dict[str, Any]
    missing: list[MissingProfileItem]
    items: list[RecommendationOut]
    notes: list[str]
