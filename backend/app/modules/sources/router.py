from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.localize import Localizer
from app.modules.sources import service
from app.modules.sources.schemas import OpportunityOut, SourceOut

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=list[SourceOut])
def list_sources(language: Literal["ta", "en"] = "en", db: Session = Depends(get_db)):
    loc = Localizer(language)
    return [
        {
            **service.source_brief(s, loc),
            "category": s.category,
            "api_access": s.api_access,
            "notes": s.notes,
        }
        for s in service.list_sources(db)
    ]


@router.get("/opportunities/{slug}", response_model=OpportunityOut)
def get_opportunity(
    slug: str,
    request: Request,
    language: Literal["ta", "en"] = "en",
    db: Session = Depends(get_db),
):
    opp = service.get_opportunity(db, slug)
    if opp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "opportunity_not_found")
    src = db.get(service.Source, opp.source_id)
    return service.opportunity_out(opp, src, language, request.app.state.settings.source_fresh_days)
