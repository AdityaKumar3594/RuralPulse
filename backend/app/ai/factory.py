from app.ai.base import LLMProvider
from app.core.config import Settings


def build_provider(settings: Settings) -> LLMProvider | None:
    """None means "no LLM configured": features fall back to deterministic behaviour."""
    if settings.llm_provider == "anthropic":
        from app.ai.anthropic_provider import AnthropicProvider

        if settings.llm_api_key is None:  # Settings validation already prevents this
            raise ValueError("LLM_API_KEY is required")
        return AnthropicProvider(
            api_key=settings.llm_api_key.get_secret_value(),
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        )
    return None
