from app.core.config import Settings
from app.integrations.speech.base import SpeechProvider


def build_speech(settings: Settings) -> SpeechProvider | None:
    """None means voice is not configured: text input and output remain the only mode."""
    if settings.bhashini_user_id and settings.bhashini_api_key:
        from app.integrations.speech.bhashini import BhashiniProvider

        return BhashiniProvider(
            user_id=settings.bhashini_user_id,
            api_key=settings.bhashini_api_key.get_secret_value(),
            pipeline_url=settings.bhashini_pipeline_url,
            pipeline_id=settings.bhashini_pipeline_id,
        )
    return None
