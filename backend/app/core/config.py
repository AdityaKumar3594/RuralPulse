from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"  # noqa: S105 - rejected in production


class Settings(BaseSettings):
    """Application settings, read from environment variables (or backend/.env)."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True, extra="ignore"
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_version: str = "0.1.0"

    database_url: str = "postgresql+psycopg://Ruralpulse:Ruralpulse@localhost:5432/Ruralpulse"
    db_connect_timeout_seconds: int = 3

    jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    access_token_minutes: int = 12 * 60
    max_failed_logins: int = 5
    login_lockout_minutes: int = 15

    # Flat overrides for the career ranking weights, e.g. RANKING_OVERRIDES='{"stage_bonus": 0}'.
    ranking_overrides: dict[str, float] = {}

    # A verified record older than this many days is reported as 'stale'.
    source_fresh_days: int = 180

    # AI provider. "none" disables LLM calls; features fall back to templates.
    llm_provider: Literal["anthropic", "none"] = "none"
    llm_model: str = "claude-sonnet-5-5"
    llm_api_key: SecretStr | None = None
    llm_timeout_seconds: int = 20
    # AI-written explanations per student per day; beyond it the deterministic template is used.
    ai_daily_limit: int = 30

    # Optional BHASHINI speech/translation credentials.
    bhashini_user_id: str | None = None
    bhashini_api_key: SecretStr | None = None
    # Endpoint and pipeline id come from BHASHINI's public docs; they are settings so they can be
    # corrected without a code change if the service moves.
    bhashini_pipeline_url: str = (
        "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
    )
    bhashini_pipeline_id: str = "64392f96daac500b55c543cd"
    max_audio_bytes: int = 1_000_000  # ~30 s of 16 kHz mono WAV
    max_tts_chars: int = 500

    @model_validator(mode="after")
    def _check_consistency(self) -> "Settings":
        if self.app_env == "production":
            secret = self.jwt_secret.get_secret_value()
            if secret == DEV_JWT_SECRET or len(secret) < 32:
                raise ValueError("JWT_SECRET must be set to a value of at least 32 characters")
        if self.llm_provider != "none" and self.llm_api_key is None:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER is not 'none'")
        if (self.bhashini_user_id is None) != (self.bhashini_api_key is None):
            raise ValueError("BHASHINI_USER_ID and BHASHINI_API_KEY must be set together")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
