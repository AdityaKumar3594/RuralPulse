import base64
import json

import httpx2 as httpx
import pytest

from app.integrations.speech.base import SpeechProvider, SpeechUnavailable
from app.integrations.speech.bhashini import BhashiniProvider
from app.integrations.speech.factory import build_speech
from app.main import create_app
from tests.conftest import auth_headers, make_settings, register

PIPELINE = "https://pipeline.test/getModelsPipeline"
INFERENCE = "https://inference.test/compute"
WAV = b"RIFF" + b"\x24\x00\x00\x00" + b"WAVE" + b"\x00" * 60


def config_response(service="svc-ta"):
    return {
        "pipelineResponseConfig": [{"config": [{"serviceId": service}]}],
        "pipelineInferenceAPIEndPoint": {
            "callbackUrl": INFERENCE,
            "inferenceApiKey": {"name": "Authorization", "value": "inference-secret"},
        },
    }


def provider_with(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return BhashiniProvider("user-1", "api-key-1", PIPELINE, "pipe-1", client=client)


class Recorder:
    def __init__(self, compute_body):
        self.requests = []
        self.compute_body = compute_body

    def __call__(self, request):
        body = json.loads(request.content)
        self.requests.append((str(request.url), dict(request.headers), body))
        if str(request.url) == PIPELINE:
            return httpx.Response(200, json=config_response())
        return httpx.Response(200, json=self.compute_body)


# --- adapter against a mocked service (never against the live one) ---


def test_transcribe_follows_the_documented_two_step_flow():
    rec = Recorder({"pipelineResponse": [{"output": [{"source": "  வணக்கம்  "}]}]})
    text = provider_with(rec).transcribe(WAV, "ta")
    assert text == "வணக்கம்"
    (url1, headers1, body1), (url2, headers2, body2) = rec.requests
    assert (
        url1 == PIPELINE
        and headers1["userid"] == "user-1"
        and headers1["ulcaapikey"] == "api-key-1"
    )
    assert body1["pipelineTasks"][0] == {
        "taskType": "asr",
        "config": {"language": {"sourceLanguage": "ta"}},
    }
    assert body1["pipelineRequestConfig"] == {"pipelineId": "pipe-1"}
    assert url2 == INFERENCE and headers2["authorization"] == "inference-secret"
    task = body2["pipelineTasks"][0]
    assert task["taskType"] == "asr" and task["config"]["serviceId"] == "svc-ta"
    assert task["config"]["audioFormat"] == "wav" and task["config"]["samplingRate"] == 16000
    assert base64.b64decode(body2["inputData"]["audio"][0]["audioContent"]) == WAV


def test_synthesize_decodes_the_returned_audio():
    audio = b"RIFF....WAVEdata"
    rec = Recorder(
        {"pipelineResponse": [{"audio": [{"audioContent": base64.b64encode(audio).decode()}]}]}
    )
    assert provider_with(rec).synthesize("வணக்கம்", "ta") == audio
    _, _, body = rec.requests[1]
    assert body["inputData"] == {"input": [{"source": "வணக்கம்"}]}
    assert body["pipelineTasks"][0]["taskType"] == "tts"


def test_pipeline_config_is_cached_between_calls():
    rec = Recorder({"pipelineResponse": [{"output": [{"source": "a"}]}]})
    p = provider_with(rec)
    p.transcribe(WAV, "ta")
    p.transcribe(WAV, "ta")
    assert [u for u, *_ in rec.requests].count(PIPELINE) == 1
    p.transcribe(WAV, "en")
    assert [u for u, *_ in rec.requests].count(
        PIPELINE
    ) == 2  # a different language is a new config


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, json={"message": "bad key"}),
        httpx.Response(500),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json=[1, 2]),
        httpx.Response(200, json={"no": "config"}),
    ],
)
def test_service_errors_become_speech_unavailable_without_leaking_details(response):
    p = provider_with(lambda request: response)
    with pytest.raises(SpeechUnavailable) as exc:
        p.transcribe(WAV, "ta")
    assert "api-key-1" not in str(exc.value) and "bad key" not in str(exc.value)


def test_network_failures_and_malformed_results_are_handled():
    def boom(request):
        raise httpx.ConnectError("down")

    with pytest.raises(SpeechUnavailable, match="ConnectError"):
        provider_with(boom).transcribe(WAV, "ta")
    for body in (
        {"pipelineResponse": []},
        {"pipelineResponse": [{"output": []}]},
        {"pipelineResponse": [{"output": [{"source": 5}]}]},
    ):
        with pytest.raises(SpeechUnavailable):
            provider_with(Recorder(body)).transcribe(WAV, "ta")
    for body in (
        {"pipelineResponse": [{"audio": [{"audioContent": "!!!"}]}]},
        {"pipelineResponse": [{"audio": [{"audioContent": ""}]}]},
    ):
        with pytest.raises(SpeechUnavailable):
            provider_with(Recorder(body)).synthesize("x", "ta")


def test_the_adapter_never_claims_to_be_live_tested():
    assert BhashiniProvider.live_tested is False


def test_factory_builds_only_with_both_credentials():
    assert build_speech(make_settings()) is None
    built = build_speech(make_settings(bhashini_user_id="u", bhashini_api_key="k"))
    assert isinstance(built, BhashiniProvider)


# --- endpoints ---


class FakeSpeech(SpeechProvider):
    name = "fake"

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def transcribe(self, audio_wav, language):
        self.calls.append(("stt", len(audio_wav), language))
        if self.fail:
            raise SpeechUnavailable("http_500")
        return "வணக்கம்"

    def synthesize(self, text, language):
        self.calls.append(("tts", text, language))
        if self.fail:
            raise SpeechUnavailable("http_500")
        return WAV


@pytest.fixture
def student(client_with_db):
    h = auth_headers(register(client_with_db))
    client_with_db.post("/api/consents", json={"given_by": "self"}, headers=h)
    return h


@pytest.fixture
def voice_client(settings):
    from fastapi.testclient import TestClient

    def build(speech=None, **overrides):
        s = settings.model_copy(update=overrides) if overrides else settings
        return TestClient(create_app(s, speech=speech))

    return build


def test_capabilities_report_what_is_really_available(client_with_db, voice_client):
    caps = client_with_db.get("/api/capabilities").json()
    assert caps == {
        "speech_to_text": False,
        "text_to_speech": False,
        "provider": None,
        "live_tested": False,
        "ai_explanations": False,
        "languages": ["ta", "en"],
    }
    with_voice = voice_client(FakeSpeech()).get("/api/capabilities").json()
    assert with_voice["speech_to_text"] and with_voice["provider"] == "fake"
    assert with_voice["live_tested"] is False  # configured is not the same as proven


def test_without_a_provider_speech_endpoints_say_so(client_with_db, student):
    r = client_with_db.post("/api/speech/transcribe", content=WAV, headers=student)
    assert (r.status_code, r.json()["detail"]) == (503, "speech_not_configured")
    r = client_with_db.post("/api/speech/synthesize", json={"text": "hi"}, headers=student)
    assert (r.status_code, r.json()["detail"]) == (503, "speech_not_configured")


def test_transcribe_and_synthesize_happy_path(voice_client, student):
    fake = FakeSpeech()
    client = voice_client(fake)
    r = client.post("/api/speech/transcribe?language=ta", content=WAV, headers=student)
    assert r.status_code == 200 and r.json() == {"text": "வணக்கம்", "language": "ta"}
    r = client.post(
        "/api/speech/synthesize", json={"text": "வணக்கம்", "language": "ta"}, headers=student
    )
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and r.content == WAV
    assert r.headers["cache-control"] == "no-store"
    assert fake.calls == [("stt", len(WAV), "ta"), ("tts", "வணக்கம்", "ta")]


def test_input_validation_and_limits(voice_client, student):
    client = voice_client(FakeSpeech(), max_audio_bytes=100, max_tts_chars=10)
    assert (
        client.post(
            "/api/speech/transcribe", content=b"not audio at all" * 5, headers=student
        ).status_code
        == 422
    )
    assert client.post("/api/speech/transcribe", content=b"", headers=student).status_code == 422
    assert (
        client.post(
            "/api/speech/transcribe", content=WAV + b"\x00" * 200, headers=student
        ).status_code
        == 413
    )
    assert (
        client.post("/api/speech/transcribe?language=fr", content=WAV, headers=student).status_code
        == 422
    )
    assert (
        client.post("/api/speech/synthesize", json={"text": "x" * 11}, headers=student).status_code
        == 422
    )
    assert (
        client.post("/api/speech/synthesize", json={"text": ""}, headers=student).status_code == 422
    )
    assert (
        client.post(
            "/api/speech/synthesize", json={"text": "hi", "language": "fr"}, headers=student
        ).status_code
        == 422
    )


def test_provider_failures_surface_as_bad_gateway_not_a_fake_success(voice_client, student):
    client = voice_client(FakeSpeech(fail=True))
    assert (
        client.post("/api/speech/transcribe", content=WAV, headers=student).json()["detail"]
        == "speech_unavailable"
    )
    r = client.post("/api/speech/synthesize", json={"text": "hi"}, headers=student)
    assert (r.status_code, r.json()["detail"]) == (502, "speech_unavailable")


def test_speech_needs_login_and_consent_and_is_audited_without_content(
    voice_client, client_with_db, student, db
):
    from sqlalchemy import select

    from app.core.audit import AuditEvent

    client = voice_client(FakeSpeech())
    assert client.post("/api/speech/transcribe", content=WAV).status_code == 401
    no_consent = auth_headers(register(client_with_db, phone="9000000007"))
    assert client.post("/api/speech/transcribe", content=WAV, headers=no_consent).status_code == 403
    client.post("/api/speech/transcribe", content=WAV, headers=student)
    [event] = db.scalars(select(AuditEvent).where(AuditEvent.action == "speech.transcribed")).all()
    assert event.detail == {"bytes": len(WAV)}
