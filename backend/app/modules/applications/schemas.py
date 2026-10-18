import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.applications.models import ExternalStatus, InternalStatus


class SaveRequest(BaseModel):
    opportunity: str = Field(max_length=60)
    language: Literal["ta", "en"] = "en"


class UpdateRequest(BaseModel):
    internal_status: InternalStatus | None = None
    note: str | None = Field(default=None, max_length=1000)
    documents: dict[str, bool] | None = None
    # What the student says happened. Stored as an unconfirmed report.
    reported_external_status: ExternalStatus | None = None

    @model_validator(mode="after")
    def _something(self) -> "UpdateRequest":
        if not self.model_fields_set:
            raise ValueError("nothing to update")
        return self


class HelpIn(BaseModel):
    message: str | None = Field(default=None, max_length=500)


class ApplicationOut(BaseModel):
    id: uuid.UUID
    opportunity: dict[str, Any]
    # Our tracking of what the student says they did. NOT proof that anything was submitted.
    internal_status: str
    note: str | None
    documents: dict[str, bool]
    # What the provider did, with who said so. Only `external_confirmed` may be shown as fact.
    external_status: str
    external_status_source: str | None
    external_confirmed: bool
    external_status_at: datetime | None
    external_status_note: str | None
    reference_code: str
    created_at: datetime
    updated_at: datetime
