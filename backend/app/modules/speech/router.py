from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.audit import audit
from app.core.db import get_db
from app.integrations.speech.base import SpeechProvider, SpeechUnavailable
from app.modules.identity.deps import require_student_with_consent
from app.modules.identity.models import User

router = APIRouter(tags=["speech"])
Language = Literal["ta", "en"]


class Capabilities(BaseModel):
    speech_to_text: bool
    text_to_speech: bool
    provider: str | None
    # False until the provider has been exercised against the real service.
    live_tested: bool
    ai_explanations: bool
    languages: list[str]


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: Language = "ta"


class Transcript(BaseModel):
    text: str
    language: Language


@router.get("/capabilities", response_model=Capabilities)
def capabilities(request: Request):
    """What this deployment can really do, so the UI never offers a feature that is not there."""
    speech: SpeechProvider | None = request.app.state.speech
    return Capabilities(
        speech_to_text=speech is not None,
        text_to_speech=speech is not None,
        provider=speech.name if speech else None,
        live_tested=bool(speech and speech.live_tested),
        ai_explanations=request.app.state.llm is not None,
        languages=["ta", "en"],
    )


def _provider(request: Request) -> SpeechProvider:
    speech: SpeechProvider | None = request.app.state.speech
    if speech is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "speech_not_configured")
    return speech


@router.post("/speech/transcribe", response_model=Transcript)
async def transcribe(
    request: Request,
    language: Language = "ta",
    user: User = Depends(require_student_with_consent),
    db: Session = Depends(get_db),
):
    """Speech to text. Body: a 16 kHz mono WAV file sent as the raw request body."""
    speech = _provider(request)
    limit = request.app.state.settings.max_audio_bytes
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "audio_too_large")
    body = await request.body()
    if len(body) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "audio_too_large")
    if len(body) < 44 or body[:4] != b"RIFF" or body[8:12] != b"WAVE":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "audio_must_be_wav")
    try:
        text = await run_in_threadpool(speech.transcribe, body, language)
    except SpeechUnavailable:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "speech_unavailable") from None
    # Audit that speech was used, never the audio or the words.
    audit(db, "speech.transcribed", actor_id=user.id, subject_user_id=user.id, bytes=len(body))
    db.commit()
    return Transcript(text=text, language=language)


@router.post("/speech/synthesize")
async def synthesize(
    data: SynthesizeRequest,
    request: Request,
    user: User = Depends(require_student_with_consent),
):
    """Text to speech: returns WAV audio. The text length is capped."""
    speech = _provider(request)
    if len(data.text) > request.app.state.settings.max_tts_chars:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "text_too_long")
    try:
        audio = await run_in_threadpool(speech.synthesize, data.text, data.language)
    except SpeechUnavailable:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "speech_unavailable") from None
    return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "no-store"})
