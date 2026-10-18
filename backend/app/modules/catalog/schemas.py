from typing import Any

from pydantic import BaseModel

from app.modules.sources.schemas import OpportunityBrief


class CareerBrief(BaseModel):
    slug: str
    family: str
    title: str | None


class RouteOut(BaseModel):
    kind: str
    title: str | None
    min_stage: str | None
    opportunity: OpportunityBrief | None


class CareerOut(CareerBrief):
    description: str | None
    activities: list[str]
    skills: list[str]
    entry: dict[str, Any]
    routes: list[RouteOut]
    related: list[CareerBrief]
    learning_resources: list[OpportunityBrief]
    source_refs: list[dict[str, str]]
    verification_status: str
    human_reviewed: bool
    localization_status: str
    language: str
    language_fallback: bool
