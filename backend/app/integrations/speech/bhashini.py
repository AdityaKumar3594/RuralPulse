"""BHASHINI (India's national language mission) speech adapter.

Flow, per the public BHASHINI/ULCA documentation (bhashini.gitbook.io/bhashini-apis):
  1. "Pipeline config": POST {pipeline_url} with headers userID + ulcaApiKey and the task
     (asr or tts) and language. The response names a serviceId, the inference endpoint and an
     inference key.
  2. "Pipeline compute": POST the inference endpoint with the inference key header and the
     audio (base64) or text.

STATUS: written from the documentation and tested only against a mocked transport. It has NOT
been run against the live service (no credentials were available, and Tamil support is not
confirmed in the docs). `live_tested` therefore stays False; flip it only after a real call.
"""

import base64
import time
from typing import Any

import httpx2 as httpx

from app.integrations.speech.base import SpeechProvider, SpeechUnavailable

CONFIG_TTL_SECONDS = 3600


class BhashiniProvider(SpeechProvider):
    name = "bhashini"
    live_tested = False

    def __init__(
        self,
        user_id: str,
        api_key: str,
        pipeline_url: str,
        pipeline_id: str,
        timeout: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._headers = {"userID": user_id, "ulcaApiKey": api_key}
        self._pipeline_url = pipeline_url
        self._pipeline_id = pipeline_id
        self._client = client or httpx.Client(timeout=timeout)
        self._configs: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}

    # -- plumbing -----------------------------------------------------------------------------

    def _post(self, url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise SpeechUnavailable(type(exc).__name__) from exc  # class only: no content leaks
        if response.status_code != 200:
            raise SpeechUnavailable(f"http_{response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise SpeechUnavailable("invalid_json") from exc
        if not isinstance(data, dict):
            raise SpeechUnavailable("unexpected_response")
        return data

    def _config(self, task: str, language: str) -> dict[str, Any]:
        key = (task, language)
        cached = self._configs.get(key)
        if cached and time.monotonic() - cached[0] < CONFIG_TTL_SECONDS:
            return cached[1]
        data = self._post(
            self._pipeline_url,
            self._headers,
            {
                "pipelineTasks": [
                    {"taskType": task, "config": {"language": {"sourceLanguage": language}}}
                ],
                "pipelineRequestConfig": {"pipelineId": self._pipeline_id},
            },
        )
        try:
            service_id = data["pipelineResponseConfig"][0]["config"][0]["serviceId"]
            endpoint = data["pipelineInferenceAPIEndPoint"]
            config = {
                "service_id": service_id,
                "url": endpoint["callbackUrl"],
                "key_name": endpoint["inferenceApiKey"]["name"],
                "key_value": endpoint["inferenceApiKey"]["value"],
            }
        except (KeyError, IndexError, TypeError) as exc:
            raise SpeechUnavailable("no_service_for_language") from exc
        self._configs[key] = (time.monotonic(), config)
        return config

    def _compute(
        self, task: str, language: str, task_config: dict[str, Any], input_data: dict
    ) -> dict:
        cfg = self._config(task, language)
        data = self._post(
            cfg["url"],
            {cfg["key_name"]: cfg["key_value"]},
            {
                "pipelineTasks": [
                    {
                        "taskType": task,
                        "config": {
                            "language": {"sourceLanguage": language},
                            "serviceId": cfg["service_id"],
                            **task_config,
                        },
                    }
                ],
                "inputData": input_data,
            },
        )
        try:
            result = data["pipelineResponse"][0]
        except (KeyError, IndexError, TypeError) as exc:
            raise SpeechUnavailable("unexpected_response") from exc
        if not isinstance(result, dict):
            raise SpeechUnavailable("unexpected_response")
        return result

    # -- interface ----------------------------------------------------------------------------

    def transcribe(self, audio_wav: bytes, language: str) -> str:
        result = self._compute(
            "asr",
            language,
            {"audioFormat": "wav", "samplingRate": 16000},
            {"audio": [{"audioContent": base64.b64encode(audio_wav).decode("ascii")}]},
        )
        try:
            text = result["output"][0]["source"]
        except (KeyError, IndexError, TypeError) as exc:
            raise SpeechUnavailable("no_transcript") from exc
        if not isinstance(text, str):
            raise SpeechUnavailable("no_transcript")
        return text.strip()

    def synthesize(self, text: str, language: str) -> bytes:
        result = self._compute("tts", language, {"gender": "female"}, {"input": [{"source": text}]})
        try:
            audio = base64.b64decode(result["audio"][0]["audioContent"], validate=True)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise SpeechUnavailable("no_audio") from exc
        if not audio:
            raise SpeechUnavailable("no_audio")
        return audio
