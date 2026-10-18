from fastapi import FastAPI

from app.ai.base import LLMProvider
from app.ai.factory import build_provider
from app.core import health
from app.core.config import Settings, get_settings
from app.core.db import make_engine, make_session_factory
from app.integrations.speech.base import SpeechProvider
from app.integrations.speech.factory import build_speech
from app.modules.admin.router import router as admin_router
from app.modules.applications.router import router as applications_router
from app.modules.catalog.router import router as catalog_router
from app.modules.eligibility.router import router as eligibility_router
from app.modules.explain.router import router as explain_router
from app.modules.facilitator.router import router as facilitator_router
from app.modules.facilitator.router import student_router as me_router
from app.modules.identity.router import router as identity_router
from app.modules.interview.router import router as interview_router
from app.modules.partners.router import router as partners_router
from app.modules.pathway.router import router as pathway_router
from app.modules.profile.router import router as profile_router
from app.modules.recommend.engine import RankingConfig
from app.modules.recommend.router import router as recommend_router
from app.modules.retrieval.router import router as retrieval_router
from app.modules.sources.router import router as sources_router
from app.modules.speech.router import router as speech_router
from app.modules.training.router import router as training_router


def create_app(
    settings: Settings | None = None,
    llm: LLMProvider | None = None,
    speech: SpeechProvider | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    is_prod = settings.app_env == "production"

    app = FastAPI(
        title="Ruralpulse API",
        version=settings.app_version,
        docs_url=None if is_prod else "/api/docs",
        openapi_url=None if is_prod else "/api/openapi.json",
    )
    app.state.settings = settings
    app.state.engine = make_engine(settings)
    app.state.session_factory = make_session_factory(app.state.engine)
    app.state.llm = llm if llm is not None else build_provider(settings)
    app.state.speech = speech if speech is not None else build_speech(settings)
    app.state.ranking_config = RankingConfig.from_overrides(settings.ranking_overrides)

    app.include_router(health.router, prefix="/api")
    app.include_router(identity_router, prefix="/api")
    app.include_router(profile_router, prefix="/api")
    app.include_router(interview_router, prefix="/api")
    app.include_router(catalog_router, prefix="/api")
    app.include_router(sources_router, prefix="/api")
    app.include_router(retrieval_router, prefix="/api")
    app.include_router(eligibility_router, prefix="/api")
    app.include_router(recommend_router, prefix="/api")
    app.include_router(pathway_router, prefix="/api")
    app.include_router(explain_router, prefix="/api")
    app.include_router(speech_router, prefix="/api")
    for r in (
        admin_router,
        applications_router,
        facilitator_router,
        me_router,
        partners_router,
        training_router,
    ):
        app.include_router(r, prefix="/api")
    return app


app = create_app()
