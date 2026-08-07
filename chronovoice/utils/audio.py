"""Small audio helpers shared across the project."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

from chronovoice.core.constants import MAX_REFERENCE_SECONDS, REFERENCE_SAMPLE_RATE
from chronovoice.core.exceptions import InvalidReferenceAudio
from chronovoice.core.logger import get_logger

logger = get_logger(__name__)

#: Standard WAV header length for a PCM file with an unchanged format chunk.
WAV_HEADER_LENGTH: int = 44

#: Number of milliseconds in one second.
_MS_PER_SECOND: int = 1000


def read_wav_sample_rate(path: str | Path) -> int:
    """Read the sample rate from a WAV file header.

    Args:
        path: Path to the WAV file.

    Returns:
        The sample rate in Hz.

    Raises:
        InvalidReferenceAudio: If the file is not a readable WAV file.
    """
    audio_path = Path(path)
    try:
        header = audio_path.read_bytes()
    except (OSError, PermissionError) as exc:
        raise InvalidReferenceAudio(f"Could not read audio file: {audio_path}") from exc

    if len(header) < WAV_HEADER_LENGTH or not header.startswith(b"RIFF"):
        raise InvalidReferenceAudio(
            f"Not a valid RIFF/WAV file: {audio_path}"
        )
    # Sample rate is stored at byte offset 24 as a 32-bit little-endian int.
    return struct.unpack("<I", header[24:28])[0]


def ensure_wav(path: str | Path) -> Path:
    """Validate that a path points to a readable WAV file.

    Args:
        path: Path to validate.

    Returns:
        The resolved path.

    Raises:
        InvalidReferenceAudio: If the file is not a WAV file.
    """
    audio_path = Path(path)
    if not audio_path.is_file():
        raise InvalidReferenceAudio(f"Audio file not found: {audio_path}")
    read_wav_sample_rate(audio_path)
    return audio_path


def read_wav_duration(path: str | Path) -> float:
    """Read the duration of a WAV file in seconds.

    Uses only the standard library so it works without pydub/ffmpeg.

    Args:
        path: Path to the WAV file.

    Returns:
        Duration in seconds.

    Raises:
        InvalidReferenceAudio: If the file is not a readable WAV file.
    """
    audio_path = Path(path)
    if not audio_path.is_file():
        raise InvalidReferenceAudio(f"Audio file not found: {audio_path}")
    try:
        with wave.open(str(audio_path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
    except (wave.Error, OSError, ValueError) as exc:
        raise InvalidReferenceAudio(
            f"Could not read WAV duration: {audio_path}"
        ) from exc
    if rate <= 0:
        raise InvalidReferenceAudio(f"Invalid sample rate in WAV: {audio_path}")
    return frames / rate


def prepare_reference(
    source: str | Path,
    target: str | Path,
    sample_rate: int = REFERENCE_SAMPLE_RATE,
    max_seconds: float = MAX_REFERENCE_SECONDS,
) -> Path:
    """Normalize an arbitrary audio clip into a voice reference WAV.

    Decodes the source (MP3, WAV, OGG, ...) via pydub/ffmpeg, keeps only
    the first ``max_seconds`` of audio, resamples to ``sample_rate`` in mono,
    and exports the result as a WAV file at ``target``.

    Args:
        source: Path of the source clip.
        target: Path where the normalized WAV should be written.
        sample_rate: Target sample rate in Hz.
        max_seconds: Maximum duration to keep, in seconds.

    Returns:
        The resolved target path.

    Raises:
        InvalidReferenceAudio: If the source cannot be decoded (missing
            pydub/ffmpeg or a corrupted file).
    """
    source_path = Path(source)
    target_path = Path(target)
    if not source_path.is_file():
        raise InvalidReferenceAudio(f"Reference audio not found: {source_path}")

    try:
        from pydub import AudioSegment  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - depends on env
        raise InvalidReferenceAudio(
            "pydub is required to convert reference audio. Install it with "
            "'pip install -e \".[xtts]\"' or 'pip install pydub'."
        ) from exc

    try:
        audio = AudioSegment.from_file(str(source_path))
    except Exception as exc:  # noqa: BLE001 - ffmpeg/pydub raise varied errors
        raise InvalidReferenceAudio(
            f"Could not decode reference audio {source_path}. "
            "Ensure ffmpeg is installed on the system."
        ) from exc

    target_path.parent.mkdir(parents=True, exist_ok=True)
    audio = audio[: int(max_seconds * _MS_PER_SECOND)]
    audio = audio.set_frame_rate(sample_rate).set_channels(1)
    audio.export(str(target_path), format="wav")

    logger.info(
        "Prepared reference audio",
        extra={
            "context": {
                "source": str(source_path),
                "target": str(target_path),
                "sample_rate": sample_rate,
                "max_seconds": max_seconds,
            }
        },
    )
    return target_path