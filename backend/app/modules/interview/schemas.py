import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class OptionOut(BaseModel):
    value: str
    label: str


class QuestionOut(BaseModel):
    id: str
    field_key: str
    kind: Literal["single_choice", "list_text", "number", "short_text"]
    prompt: str
    why: str
    options: list[OptionOut]
    min_value: int | None = None
    max_value: int | None = None


class ProgressOut(BaseModel):
    answered: int
    total: int


class SessionOut(BaseModel):
    id: uuid.UUID
    status: Literal["active", "completed"]
    language: str
    question: QuestionOut | None
    progress: ProgressOut


class StartRequest(BaseModel):
    language: Literal["ta", "en"] | None = None


class AnswerRequest(BaseModel):
    """`value`: a structured choice/number/list from the UI. `text`: free text to interpret."""

    question_id: str = Field(max_length=50)
    kind: Literal["value", "text", "unknown", "skip"]
    value: Any = None
    text: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _shape(self) -> "AnswerRequest":
        if self.kind == "value" and self.value is None:
            raise ValueError("value is required for kind=value")
        if self.kind == "text" and not (self.text and self.text.strip()):
            raise ValueError("text is required for kind=text")
        if self.kind in ("unknown", "skip") and (self.value is not None or self.text):
            raise ValueError(f"kind={self.kind} takes no value or text")
        if self.kind == "value" and self.text:
            raise ValueError("send either value or text, not both")
        if self.kind == "text" and self.value is not None:
            raise ValueError("send either value or text, not both")
        return self


class AnswerResult(BaseModel):
    outcome: Literal["recorded", "unknown", "skipped", "needs_clarification"]
    corrected: bool
    interpreted_by: Literal["student", "deterministic", "ai"] | None
    message: str | None
    session: SessionOut
