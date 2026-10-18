"""Imports every module's models so Alembic and tests see the full metadata."""

from app.core.audit import AuditEvent
from app.modules.applications.models import Application
from app.modules.catalog.models import Career
from app.modules.eligibility.models import EligibilityEvaluation
from app.modules.explain.models import Explanation
from app.modules.facilitator.models import (
    Endorsement,
    FacilitatorAssignment,
    HelpRequest,
    RecommendationReview,
)
from app.modules.identity.models import Consent, User
from app.modules.interview.models import InterviewAnswer, InterviewSession
from app.modules.partners.models import OpportunitySubmission, Provider, ProviderMember
from app.modules.pathway.models import PathwayPlan, PathwayStepProgress
from app.modules.profile.models import ProfileEntry
from app.modules.recommend.models import RecommendationRun
from app.modules.sources.models import Opportunity, Source
from app.modules.training.models import ModuleEnrollment, TrainingModule

__all__ = [
    "Application",
    "AuditEvent",
    "Career",
    "Consent",
    "EligibilityEvaluation",
    "Endorsement",
    "Explanation",
    "FacilitatorAssignment",
    "HelpRequest",
    "InterviewAnswer",
    "InterviewSession",
    "ModuleEnrollment",
    "Opportunity",
    "OpportunitySubmission",
    "PathwayPlan",
    "PathwayStepProgress",
    "ProfileEntry",
    "Provider",
    "ProviderMember",
    "RecommendationReview",
    "RecommendationRun",
    "Source",
    "TrainingModule",
    "User",
]
