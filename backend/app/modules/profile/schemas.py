import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provenance: str
    value: Any
    verification: str
    source: str
    basis: str | None
    created_at: datetime


class FieldView(BaseModel):
    key: str
    description: str
    state: Literal["established", "hypothesis_only", "unknown"]
    conflict: bool
    entries: list[EntryOut]


class ProfileOut(BaseModel):
    fields: list[FieldView]


class FieldUpdate(BaseModel):
    """Student statement: either a value, or `unknown: true` ("I don't know")."""

    value: Any = None
    unknown: bool = False

    @model_validator(mode="after")
    def _exactly_one(self) -> "FieldUpdate":
        if self.unknown == (self.value is not None):
            raise ValueError("send either a value or unknown=true")
        return self
