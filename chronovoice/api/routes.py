"""HTTP routes exposing the synthesis service.

All heavy operations run in a thread pool to avoid blocking the event loop
since synthesis is CPU/GPU bound.
"""

from __future__ import annotations

import asyncio
from functools import partial
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from chronovoice.api.schemas import (
    HealthResponse,
    TTSRequest,
    TTSResponse,
    VoiceCreateRequest,
    VoiceResponse,
)
from chronovoice.service.tts_service import TTSService
from chronovoice.voices.models import VoiceMetadata

router = APIRouter()


def _get_service() -> TTSService:
    """Return the application-wide synthesis service.

    Returns:
        The shared :class:`TTSService` instance.
    """
    from chronovoice.service.tts_service import get_default_service

    return get_default_service()


def _dto(result: object) -> TTSResponse:
    """Convert a synthesis result into an API response.

    Args:
        result: The :class:`SynthesisResult` from the service.

    Returns:
        A :class:`TTSResponse` payload.
    """
    output_path = str(getattr(result, "output_path"))
    chunk_count = int(getattr(result, "chunk_count"))
    return TTSResponse(output_path=output_path, chunk_count=chunk_count)


@router.get("/health", response_model=HealthResponse)
async def health(
    service: Annotated[TTSService, Depends(_get_service)],
) -> HealthResponse:
    """Return backend health and capability information.

    Args:
        service: The injected synthesis service.

    Returns:
        A :class:`HealthResponse`.
    """
    return HealthResponse(**service.health())


@router.get("/voices", response_model=list[VoiceResponse])
async def list_voices(
    service: Annotated[TTSService, Depends(_get_service)],
) -> list[VoiceResponse]:
    """List the registered voices.

    Args:
        service: The injected synthesis service.

    Returns:
        A list of :class:`VoiceResponse` objects.
    """
    voices: list[VoiceMetadata] = await asyncio.to_thread(service.voices_list)
    return [VoiceResponse(**voice.model_dump()) for voice in voices]


@router.post("/voices/create", response_model=VoiceResponse)
async def create_voice(
    request: VoiceCreateRequest,
    service: Annotated[TTSService, Depends(_get_service)],
) -> VoiceResponse:
    """Register a new voice from a reference clip.

    Args:
        request: The voice creation payload.
        service: The injected synthesis service.

    Returns:
        The newly created :class:`VoiceResponse`.
    """
    created: VoiceMetadata = await asyncio.to_thread(
        service.voice_create,
        voice_name=request.voice_name,
        reference_audio=request.reference_audio,
        language=request.language,
        description=request.description,
        sample_rate=request.sample_rate,
    )
    return VoiceResponse(**created.model_dump())


@router.post("/tts", response_model=TTSResponse)
async def synthesize(
    request: TTSRequest,
    service: Annotated[TTSService, Depends(_get_service)],
) -> TTSResponse:
    """Synthesise narration text and return the output path.

    Args:
        request: The generation payload.
        service: The injected synthesis service.

    Returns:
        A :class:`TTSResponse` describing where the audio was written.
    """
    result = await asyncio.to_thread(
        partial(
            service.synthesize,
            request.text,
            voice_name=request.voice,
            output_path=request.output_path,
        )
    )
    return _dto(result)


@router.post("/tts/file", response_class=FileResponse)
async def synthesize_file(
    request: TTSRequest,
    service: Annotated[TTSService, Depends(_get_service)],
) -> FileResponse:
    """Synthesise narration and stream the generated audio file.

    Args:
        request: The generation payload.
        service: The injected synthesis service.

    Returns:
        The generated audio as a :class:`FileResponse`.
    """
    result = await asyncio.to_thread(
        partial(
            service.synthesize,
            request.text,
            voice_name=request.voice,
            output_path=request.output_path,
        )
    )
    return FileResponse(result.output_path, media_type="audio/wav")