from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.localize import Localizer
from app.modules.catalog import service
from app.modules.catalog.schemas import CareerBrief, CareerOut
from app.modules.catalog.seed_schema import CareerFamily

router = APIRouter(tags=["catalog"])


@router.get("/careers", response_model=list[CareerBrief])
def list_careers(
    family: CareerFamily | None = None,
    language: Literal["ta", "en"] = "en",
    db: Session = Depends(get_db),
):
    loc = Localizer(language)
    return [service.career_brief(c, loc) for c in service.list_careers(db, family)]


@router.get("/careers/{slug}", response_model=CareerOut)
def get_career(slug: str, language: Literal["ta", "en"] = "en", db: Session = Depends(get_db)):
    career = service.get_career(db, slug)
    if career is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "career_not_found")
    return service.career_out(db, career, language)
