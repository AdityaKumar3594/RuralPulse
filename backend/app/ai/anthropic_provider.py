import json
from typing import Any

import anthropic

from app.ai.base import LLMProvider, LLMUnavailable, StructuredResult


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self, api_key: str, model: str, timeout: float = 20.0, client: Any | None = None
    ) -> None:
        self._model = model
        self.model = model
        self._client = client or anthropic.Anthropic(
            api_key=api_key, timeout=timeout, max_retries=1
        )

    def extract_json(
        self, *, system: str, user: str, schema: dict[str, Any], max_tokens: int = 1024
    ) -> StructuredResult:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={
                    "effort": "low",  # short extraction task; no need for deep reasoning
                    "format": {"type": "json_schema", "schema": schema},
                },
            )
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
            # Only the exception class is kept: messages could echo request content.
            raise LLMUnavailable(type(exc).__name__) from exc

        if response.stop_reason == "refusal":
            return StructuredResult(data=None, refused=True)
        if response.stop_reason != "end_turn":
            raise LLMUnavailable(f"stop_reason={response.stop_reason}")
        text = next((b.text for b in response.content if b.type == "text"), None)
        try:
            data = json.loads(text) if text else None
        except json.JSONDecodeError as exc:
            raise LLMUnavailable("invalid_json") from exc
        if not isinstance(data, dict):
            raise LLMUnavailable("not_an_object")
        return StructuredResult(data=data)
