from types import SimpleNamespace

import anthropic
import pytest

from app.ai.anthropic_provider import AnthropicProvider
from app.ai.base import LLMUnavailable
from app.ai.factory import build_provider
from tests.conftest import make_settings

SCHEMA = {"type": "object", "properties": {}, "additionalProperties": False}


def message(stop_reason="end_turn", text='{"a": 1}'):
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)] if text else []
    )


class FakeClient:
    def __init__(self, result):
        self.result, self.kwargs = result, None
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def provider(result):
    client = FakeClient(result)
    return AnthropicProvider("key", "claude-sonnet-5-5", client=client), client


def test_request_uses_structured_output_low_effort_and_no_removed_params():
    p, client = provider(message())
    assert p.extract_json(system="s", user="u", schema=SCHEMA).data == {"a": 1}
    kw = client.kwargs
    assert kw["model"] == "claude-sonnet-5-5"
    assert kw["output_config"] == {
        "effort": "low",
        "format": {"type": "json_schema", "schema": SCHEMA},
    }
    # These are rejected (400) by current models, so the provider must never send them.
    assert not {"thinking", "temperature", "top_p", "top_k", "tool_choice"} & kw.keys()
    assert kw["messages"] == [{"role": "user", "content": "u"}]


def test_refusal_is_reported_not_raised():
    p, _ = provider(message("refusal", None))
    result = p.extract_json(system="s", user="u", schema=SCHEMA)
    assert result.refused and result.data is None


@pytest.mark.parametrize(
    "result",
    [message("max_tokens"), message(text="not json"), message(text="[1, 2]"), message(text=None)],
)
def test_unusable_responses_raise_unavailable(result):
    p, _ = provider(result)
    with pytest.raises(LLMUnavailable):
        p.extract_json(system="s", user="u", schema=SCHEMA)


def test_api_errors_become_unavailable_without_leaking_message():
    err = anthropic.APIConnectionError(request=SimpleNamespace(method="POST", url="x"))
    p, _ = provider(err)
    with pytest.raises(LLMUnavailable, match="APIConnectionError"):
        p.extract_json(system="s", user="u", schema=SCHEMA)


def test_factory_builds_provider_only_when_configured():
    assert build_provider(make_settings()) is None
    built = build_provider(make_settings(llm_provider="anthropic", llm_api_key="k"))
    assert isinstance(built, AnthropicProvider)
