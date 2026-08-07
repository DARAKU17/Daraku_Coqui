"""Pydantic schemas for the FastAPI surface."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health probe response describing the active backend.

    Attributes:
        status: Always ``"ok"`` for a reachable API.
        backend: Identifier of the configured backend.
        loaded: Whether the model is currently resident.
        supports_multilingual: Backend multilingual capability.
        supports_streaming: Backend streaming capability.
        supports_voice_cloning: Backend voice cloning capability.
    """

    status: str = "ok"
    backend: str
    loaded: bool
    supports_multilingual: bool = False
    supports_streaming: bool = False
    supports_voice_cloning: bool = False


class VoiceCreateRequest(BaseModel):
    """Request payload for registering a new voice.

    Attributes:
        voice_name: Name of the new voice.
        reference_audio: Path to the source wav clip on the server.
        language: Language code of the clip.
        description: Optional human readable description.
        sample_rate: Sample rate of the clip in Hz.
    """

    voice_name: str = Field(min_length=1)
    reference_audio: str = Field(min_length=1)
    language: str = Field(default="en", min_length=2)
    description: str = Field(default="")
    sample_rate: int = Field(default=22050, ge=8000)


class VoiceResponse(BaseModel):
    """A voice as returned by the API.

    Attributes:
        voice_name: Name of the voice.
        language: Language code.
        description: Human readable description.
        created_at: Registration timestamp.
        sample_rate: Reference sample rate in Hz.
    """

    voice_name: str
    language: str
    description: str = ""
    created_at: datetime
    sample_rate: int


class TTSRequest(BaseModel):
    """Request payload for text-to-speech generation.

    Attributes:
        text: The narration text to synthesise.
        voice: Voice name to clone; defaults to the configured voice.
        language: Language override; defaults to the voice language.
        output_path: Optional destination path on the server.
    """

    text: str = Field(min_length=1)
    voice: str | None = Field(default=None)
    language: str | None = Field(default=None)
    output_path: str | None = Field(default=None)


class TTSResponse(BaseModel):
    """Response describing a completed narration generation.

    Attributes:
        output_path: Path of the generated audio file.
        chunk_count: Number of audio segments merged.
    """

    output_path: str
    chunk_count: int