from typing import Any

FALLBACK_LANG = "en"


class Localizer:
    """Picks text in the requested language, falling back to English and remembering that it did."""

    def __init__(self, lang: str) -> None:
        self.lang = lang
        self.fell_back = False

    def text(self, value: dict[str, str] | None) -> str | None:
        if not value:
            return None
        if value.get(self.lang):
            return value[self.lang]
        self.fell_back = self.fell_back or self.lang != FALLBACK_LANG
        return value.get(FALLBACK_LANG)

    def items(self, value: dict[str, list[str]] | None) -> list[str]:
        if not value:
            return []
        if value.get(self.lang):
            return value[self.lang]
        self.fell_back = self.fell_back or self.lang != FALLBACK_LANG
        return value.get(FALLBACK_LANG, [])

    def any(self, value: Any) -> Any:  # pragma: no cover - convenience for ad-hoc fields
        return self.text(value) if isinstance(value, dict) else value
