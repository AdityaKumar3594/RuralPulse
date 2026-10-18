from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class LLMUnavailable(Exception):
    """The provider is unreachable, rate limited, or returned something unusable."""


@dataclass(frozen=True)
class StructuredResult:
    data: dict[str, Any] | None
    refused: bool = False


class LLMProvider(ABC):
    """Provider-independent interface. Callers must still validate whatever comes back."""

    name: str
    model: str = "unknown"

    @abstractmethod
    def extract_json(
        self, *, system: str, user: str, schema: dict[str, Any], max_tokens: int = 1024
    ) -> StructuredResult:
        """Return a JSON object matching `schema`, or `refused=True`.

        Raise LLMUnavailable on any failure.
        """
