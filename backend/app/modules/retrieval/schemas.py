from typing import Literal

from pydantic import BaseModel

from app.modules.sources.schemas import SourceBrief, VerificationOut


class SearchHit(BaseModel):
    type: Literal["career", "opportunity"]
    id: str
    title: str | None
    summary: str | None
    # exact: every query word matched. partial: some words, word starts or near-spellings
    # matched. browse: no query, filters only. (There is no semantic matching yet.)
    match_type: Literal["exact", "partial", "browse"]
    score: float
    group: str  # opportunity kind or career family
    url: str | None
    source: SourceBrief | None
    freshness: Literal["fresh", "stale", "expired", "unverified"] | None
    verification: VerificationOut | None
    eligibility_known: bool | None
    flags: list[str]
    language_fallback: bool


class SearchResponse(BaseModel):
    query: str | None
    language: str
    search_mode: Literal["keyword"] = "keyword"
    status: Literal["ok", "partial_only", "insufficient_evidence"]
    message: str | None
    results: list[SearchHit]
