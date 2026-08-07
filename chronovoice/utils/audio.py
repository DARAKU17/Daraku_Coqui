"""Small audio helpers shared across the project."""

from __future__ import annotations

import struct
from pathlib import Path

from chronovoice.core.exceptions import InvalidReferenceAudio

#: Standard WAV header length for a PCM file with an unchanged format chunk.
WAV_HEADER_LENGTH: int = 44


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