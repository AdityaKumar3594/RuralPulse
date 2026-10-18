"""Validated shape of data/seed/careers.yaml. Unknown keys are rejected."""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.profile.fields import EducationStage

CareerFamily = Literal[
    "agriculture",
    "skilled_trades",
    "health_care",
    "education",
    "creative_crafts",
    "public_service",
    "business",
    "technology",
    "hospitality",
    "transport_logistics",
]
RouteKind = Literal[
    "iti",
    "diploma",
    "degree",
    "apprenticeship",
    "short_course",
    "on_the_job",
    "self_learning",
    "competitive_exam",
]
Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=60)]
Localized = dict[str, str]
LocalizedList = dict[str, list[str]]


def _require_english(value: dict) -> dict:
    if not value.get("en"):
        raise ValueError("an English ('en') value is required")
    return value


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Entry(Strict):
    # Typical, not official: unverified unless the record says otherwise.
    typical_min_stage: EducationStage | None = None
    notes: Localized

    _en = field_validator("notes")(_require_english)


class Route(Strict):
    kind: RouteKind
    title: Localized
    min_stage: EducationStage | None = None
    opportunity: Slug | None = None  # slug of a seeded opportunity that supports this route

    _en = field_validator("title")(_require_english)


class SourceRef(Strict):
    source: Slug  # id in sources.yaml
    note: str = Field(max_length=300)


class CareerSeed(Strict):
    slug: Slug
    family: CareerFamily
    title: Localized
    description: Localized
    activities: LocalizedList
    skills: LocalizedList
    entry: Entry
    routes: list[Route] = Field(min_length=1)
    related: list[Slug] = []
    learning_resources: list[Slug] = []
    keywords: list[str] = []
    source_refs: list[SourceRef] = []

    @field_validator("title", "description")
    @classmethod
    def _en_text(cls, v: dict) -> dict:
        return _require_english(v)

    @field_validator("activities", "skills")
    @classmethod
    def _en_list(cls, v: dict) -> dict:
        if not v.get("en"):
            raise ValueError("an English list is required")
        sizes = {len(items) for items in v.values()}
        if len(sizes) > 1:
            raise ValueError("every language must list the same number of items")
        return v

    @field_validator("description")
    @classmethod
    def _no_numbers_claims(cls, v: dict) -> dict:
        # Salaries, counts and percentages would be unsourced factual claims.
        for text in v.values():
            if re.search(r"(₹|\brs\.?\b|\bpercent\b|%|\blakh\b|\bcrore\b)", text, re.I):
                raise ValueError("descriptions must not contain money amounts or statistics")
        return v
