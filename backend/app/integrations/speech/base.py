from abc import ABC, abstractmethod


class SpeechUnavailable(Exception):
    """The speech service is unreachable, rejected the request, or returned something unusable."""


class SpeechProvider(ABC):
    """Provider-independent speech interface (speech to text, text to speech)."""

    name: str
    # Set True only after the integration has been exercised against the real service.
    live_tested: bool = False

    @abstractmethod
    def transcribe(self, audio_wav: bytes, language: str) -> str:
        """Return the text spoken in 16 kHz mono WAV audio."""

    @abstractmethod
    def synthesize(self, text: str, language: str) -> bytes:
        """Return WAV audio of the text spoken in the language."""
