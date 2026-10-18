from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.catalog.seed_schema import CareerFamily
from app.modules.profile.fields import EducationStage
from app.modules.retrieval import service
from app.modules.retrieval.schemas import SearchResponse
from app.modules.sources.seed_schema import OpportunityKind

router = APIRouter(tags=["retrieval"])


@router.get("/search", response_model=SearchResponse)
def search(
    request: Request,
    q: str | None = Query(default=None, max_length=200),
    type: Literal["career", "opportunity"] | None = None,
    kind: OpportunityKind | None = None,
    family: CareerFamily | None = None,
    state: str | None = Query(default=None, max_length=60),
    stage: EducationStage | None = None,
    language: Literal["ta", "en"] = "en",
    include_expired: bool = False,
    include_unverified: bool = True,
    limit: int = Query(default=10, ge=1, le=25),
    db: Session = Depends(get_db),
):
    """Public keyword search over approved records. Results carry source and freshness data."""
    return service.search(
        db,
        q,
        lang=language,
        filters=service.Filters(
            type=type,
            kind=kind,
            family=family,
            state=state,
            stage=stage,
            include_expired=include_expired,
            include_unverified=include_unverified,
        ),
        limit=limit,
        fresh_days=request.app.state.settings.source_fresh_days,
    )
