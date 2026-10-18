import pytest
from pydantic import ValidationError

from app.core.config import DEV_JWT_SECRET, Settings


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_defaults_are_valid_for_development():
    s = settings()
    assert s.app_env == "development"
    assert s.llm_provider == "none"


@pytest.mark.parametrize("secret", [DEV_JWT_SECRET, "too-short"])
def test_production_rejects_weak_jwt_secret(secret):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        settings(app_env="production", jwt_secret=secret)


def test_production_accepts_strong_jwt_secret():
    assert settings(app_env="production", jwt_secret="x" * 32).app_env == "production"


def test_llm_provider_requires_api_key():
    with pytest.raises(ValidationError, match="LLM_API_KEY"):
        settings(llm_provider="anthropic")
    assert settings(llm_provider="anthropic", llm_api_key="k").llm_provider == "anthropic"


def test_bhashini_credentials_must_be_set_together():
    with pytest.raises(ValidationError, match="BHASHINI"):
        settings(bhashini_user_id="user")


def test_empty_env_values_are_treated_as_unset(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("BHASHINI_USER_ID", "")
    s = settings()
    assert s.llm_api_key is None
    assert s.bhashini_user_id is None


def test_secrets_are_not_exposed_in_repr():
    s = settings(llm_provider="anthropic", llm_api_key="sk-secret-value")
    assert "sk-secret-value" not in repr(s)
