"""Custom exception hierarchy for ChronoVoice.

Every ChronoVoice-specific error subclasses :class:`ChronoVoiceError` so
callers can catch a single base type. Exception classes should stay small
and semantically distinct so the API layer can map them to HTTP status
codes without string matching.
"""

from __future__ import annotations


class ChronoVoiceError(Exception):
    """Base class for all ChronoVoice errors.

    Attributes:
        message: Human readable description of the failure.
    """

    def __init__(self, message: str) -> None:
        """Initialize the error with a descriptive message.

        Args:
            message: Human readable description of the failure.
        """
        super().__init__(message)
        self.message = message


class BackendNotLoaded(ChronoVoiceError):
    """Raised when a TTS backend is used before being loaded.

    This typically indicates ``load()`` was never called or failed, and
    there is no active model on the target device.
    """


class VoiceNotFound(ChronoVoiceError):
    """Raised when a requested voice cannot be resolved by the manager.

    Attributes:
        voice_name: The name that was looked up.
    """

    def __init__(self, voice_name: str) -> None:
        """Initialize the error with the missing voice name.

        Args:
            voice_name: The voice name that could not be found.
        """
        super().__init__(f"Voice '{voice_name}' not found in the voice library")
        self.voice_name = voice_name


class InvalidReferenceAudio(ChronoVoiceError):
    """Raised when a voice reference audio file is malformed.

    This covers missing files, unreadable files and files whose format or
    sample rate does not match what the backend requires.
    """


class UnsupportedLanguage(ChronoVoiceError):
    """Raised when a requested language is not supported by the backend.

    Attributes:
        language: The language code that was requested.
    """

    def __init__(self, language: str, supported: tuple[str, ...] | None = None) -> None:
        """Initialize the error with the unsupported language code.

        Args:
            language: The language code that was requested.
            supported: Optional tuple of supported language codes.
        """
        detail = f"Language '{language}' is not supported"
        if supported:
            detail += f" (supported: {', '.join(supported)})"
        super().__init__(detail)
        self.language = language


class GenerationFailed(ChronoVoiceError):
    """Raised when speech synthesis fails for any reason.

    Wraps backend or processing failures so callers never have to deal
    with framework specific exceptions.
    """
