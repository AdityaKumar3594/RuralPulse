from typing import Any

from app.ai.base import LLMProvider, LLMUnavailable, StructuredResult


class FakeLLM(LLMProvider):
    """Returns queued responses; an Exception in the queue is raised. Records every call."""

    name = "fake"
    model = "fake-model"

    def __init__(self, *responses: dict[str, Any] | StructuredResult | Exception) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def extract_json(self, *, system, user, schema, max_tokens=1024) -> StructuredResult:
        self.calls.append({"system": system, "user": user, "schema": schema})
        if not self.responses:
            raise LLMUnavailable("no response queued")
        response = self.responses.pop(0)
        if callable(response):  # build the reply from the prompt (e.g. to echo the evidence)
            response = response(user)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, StructuredResult):
            return response
        return StructuredResult(data=response)
