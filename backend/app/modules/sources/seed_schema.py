"""Validated shape of data/seed/sources.yaml and opportunities.yaml.

Core invariant: a structured claim (benefit amount, deadline, eligibility rules) may only be
present if `verification.verified_fields` lists that claim and the record is verified with
evidence. Unverified records carry general descriptions only. Nothing is ever auto-verified.
"""

from datetime import date
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.catalog.seed_schema import Localized, Slug, _require_english
from app.modules.profile.fields import EducationStage

SourceCategory = Literal[
    "learning_platform",
    "scholarship_portal",
    "apprenticeship_portal",
    "skilling_portal",
    "employment_portal",
    "state_portal",
    "exam_authority",
    "ministry",
]
OpportunityKind = Literal[
    "platform",
    "course",
    "scholarship",
    "scheme",
    "apprenticeship",
    "internship",
    "exam",
    "training_program",
    "mentorship",
    "job",
]
VerifiedField = Literal[
    "url", "provider", "existence", "eligibility", "benefit", "deadline", "documents", "scope"
]
# Hosts of evidence pages must be official, or belong to the record's source.
TRUSTED_SUFFIXES = (".gov.in", ".nic.in")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def https_host(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"must be an https URL: {url}")
    return parsed.hostname.lower()


def host_allowed(host: str, domains: list[str]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


class SourceSeed(Strict):
    id: Slug
    name: Localized
    publisher: str
    base_url: str
    category: SourceCategory
    allowed_domains: list[str] = Field(min_length=1)
    # What we found about machine access. "none_found" means we did not find a public API,
    # not that none exists.
    api_access: Literal["none_found", "available", "unknown"] = "unknown"
    notes: str | None = None

    _en = field_validator("name")(_require_english)

    @model_validator(mode="after")
    def _base_url_on_allowed_domain(self) -> "SourceSeed":
        if not host_allowed(https_host(self.base_url), self.allowed_domains):
            raise ValueError("base_url host is not in allowed_domains")
        return self


class Evidence(Strict):
    url: str
    note: str = Field(max_length=300)


class Verification(Strict):
    status: Literal["unverified", "verified"] = "unverified"
    verified_fields: list[VerifiedField] = []
    verified_at: date | None = None
    verified_by: str | None = None
    human_reviewed: bool = False
    evidence: list[Evidence] = []

    @model_validator(mode="after")
    def _verified_needs_proof(self) -> "Verification":
        if self.status == "verified":
            if not (
                self.verified_at and self.verified_by and self.verified_fields and self.evidence
            ):
                raise ValueError(
                    "verified records need verified_at, verified_by, verified_fields and evidence"
                )
        elif self.verified_fields or self.human_reviewed:
            raise ValueError("unverified records cannot list verified_fields or be human_reviewed")
        return self


class Eligibility(Strict):
    """Structured rules, only for criteria the source states explicitly."""

    education_stages: list[EducationStage] | None = None
    min_age: int | None = Field(default=None, ge=0, le=100)
    max_age: int | None = Field(default=None, ge=0, le=100)
    max_family_income_inr_per_year: int | None = Field(default=None, ge=0)
    # Date at which age limits are measured, if the source states one. Default: the day we check.
    age_as_on: date | None = None
    # Criteria the source states that the engine cannot evaluate (school type, marks, ...).
    # While any exist, a student who passes every modelled rule gets NEEDS_REVIEW, not ELIGIBLE.
    other_criteria: list[Localized] = []
    text: Localized | None = None  # the criteria as the source words them


class Scope(Strict):
    level: Literal["national", "state"] = "national"
    states: list[str] = []

    @model_validator(mode="after")
    def _states_match_level(self) -> "Scope":
        if (self.level == "state") != bool(self.states):
            raise ValueError("state scope needs states; national scope must not list any")
        return self


class Benefit(Strict):
    text: Localized
    amount_inr: int | None = Field(default=None, ge=0)
    period: Literal["month", "year", "one_time"] | None = None


class OpportunitySeed(Strict):
    slug: Slug
    source: Slug
    kind: OpportunityKind
    title: Localized
    summary: Localized
    provider: str
    url: str
    keywords: list[str] = []
    scope: Scope = Scope()
    eligibility: Eligibility | None = None
    required_documents: list[Annotated[str, Field(max_length=200)]] = []
    application_deadline: date | None = None
    expires_on: date | None = None
    benefits: list[Benefit] = []
    verification: Verification = Verification()

    @field_validator("title", "summary")
    @classmethod
    def _en_text(cls, v: dict) -> dict:
        return _require_english(v)

    @model_validator(mode="after")
    def _claims_need_verification(self) -> "OpportunitySeed":
        https_host(self.url)
        claimed = set(self.verification.verified_fields)
        checks = {
            "eligibility": self.eligibility is not None,
            "benefit": bool(self.benefits),
            "deadline": self.application_deadline is not None,
            "documents": bool(self.required_documents),
            "scope": self.scope.level == "state",
        }
        for name, present in checks.items():
            if present and name not in claimed:
                raise ValueError(f"'{name}' is set but not listed in verification.verified_fields")
        return self
