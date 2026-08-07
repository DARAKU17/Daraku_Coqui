"""Tests for reference audio conversion.

Conversion depends on ``pydub`` and the system ``ffmpeg`` binary; the module
skips cleanly when either is unavailable so the rest of the suite still runs.
"""

from __future__ import annotations

import shutil

import pytest


def _ffmpeg_available() -> bool:
    """Report whether a working ffmpeg binary is on the PATH.

    Returns:
        ``True`` when ffmpeg can be located, otherwise ``False``.
    """
    return shutil.which("ffmpeg") is not None


pytest.importorskip("pydub")

pytestmark = pytest.mark.skipif(
    not _ffmpeg_available(),
    reason="ffmpeg binary is required for audio conversion tests",
)

from chronovoice.utils.audio import (  # noqa: E402
    prepare_reference,
    read_wav_duration,
    read_wav_sample_rate,
)


def _make_wav(path, channels=1, sample_rate=22050, seconds=1.0) -> None:
    """Write a stdlib wav of silence.

    Args:
        path: Destination path.
        channels: Number of audio channels.
        sample_rate: Sample rate in Hz.
        seconds: Duration in seconds.
    """
    import wave

    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * int(sample_rate * seconds))


def test_read_wav_duration(tmp_path) -> None:
    """Duration should be read from a stdlib-generated wav."""
    path = tmp_path / "dur.wav"
    _make_wav(path, sample_rate=16000, seconds=1.0)
    assert read_wav_duration(path) == pytest.approx(1.0)


def test_prepare_reference_trim_and_resample(tmp_path) -> None:
    """A long source should be trimmed and resampled to the target rate."""
    source = tmp_path / "long.wav"
    _make_wav(source, channels=2, sample_rate=44100, seconds=40.0)

    target = tmp_path / "reference.wav"
    prepare_reference(source, target, sample_rate=22050, max_seconds=30.0)

    assert target.is_file()
    assert read_wav_sample_rate(target) == 22050
    assert read_wav_duration(target) <= 30.0


def test_prepare_reference_keeps_short_clip(tmp_path) -> None:
    """A short source should be resampled but not lengthened."""
    source = tmp_path / "short.wav"
    _make_wav(source, sample_rate=22050, seconds=1.0)

    target = tmp_path / "short_ref.wav"
    prepare_reference(source, target, sample_rate=16000, max_seconds=30.0)

    assert read_wav_duration(target) == pytest.approx(1.0, abs=0.05)
    assert read_wav_sample_rate(target) == 16000


def test_prepare_reference_missing_source(tmp_path) -> None:
    """A missing source should raise InvalidReferenceAudio."""
    from chronovoice.core.exceptions import InvalidReferenceAudio

    with pytest.raises(InvalidReferenceAudio):
        prepare_reference(tmp_path / "nope.mp3", tmp_path / "out.wav")