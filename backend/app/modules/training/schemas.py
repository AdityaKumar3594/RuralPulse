import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.modules.training.models import PriceType


class LessonIn(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    body: str = Field(max_length=4000)
    url: str | None = Field(default=None, max_length=300, pattern=r"^https://")


class ModuleIn(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=3, max_length=1000)
    language: Literal["ta", "en"] = "ta"
    lessons: list[LessonIn] = Field(default=[], max_length=30)
    price_type: PriceType = PriceType.FREE
    price_inr: int | None = Field(default=None, ge=1, le=100_000)


class ModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=150)
    description: str | None = Field(default=None, min_length=3, max_length=1000)
    language: Literal["ta", "en"] | None = None
    lessons: list[LessonIn] | None = Field(default=None, max_length=30)
    price_type: PriceType | None = None
    price_inr: int | None = Field(default=None, ge=1, le=100_000)


class ModuleOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    language: str
    status: str
    price_type: str
    price_inr: int | None
    lesson_titles: list[str]
    lessons: list[dict[str, Any]] | None  # null while locked
    enrolled: bool
    payment_status: str | None
    access: bool
    completed_lessons: list[int]
    # False in this prototype: there is no payment gateway, so paid modules cannot be unlocked.
    payments_available: bool
    created_at: datetime


class FacilitatorModuleOut(BaseModel):
    module: ModuleOut
    enrollments: int


class LessonProgressIn(BaseModel):
    done: bool = True
