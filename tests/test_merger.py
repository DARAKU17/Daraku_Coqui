"""Tests for audio merging.

Merging depends on ``pydub``; the test module skips cleanly when pydub is
not installed so the rest of the suite still runs.
"""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

pytest.importorskip("pydub")  # noqa: F401


def _make_segment(path: Path, seconds: float = 0.1, sample_rate: int = 16000) -> Path:
    """Write a short silent wav segment.

    Args:
        path: Destination path.
        seconds: Duration in seconds.
        sample_rate: Sample rate in Hz.

    Returns:
        The created path.
    """
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frames)
    return path


def test_merges_segments(tmp_path: Path) -> None:
    """Two segments should merge into a single file."""
    from chronovoice.processing.merger import AudioMerger

    segment_a = _make_segment(tmp_path / "a.wav")
    segment_b = _make_segment(tmp_path / "b.wav")
    output = tmp_path / "merged.wav"

    merger = AudioMerger(gap_ms=0, sample_rate=16000)
    result = merger.merge([segment_a, segment_b], output)

    assert result == output
    assert output.is_file()


def test_merger_gap(tmp_path: Path) -> None:
    """A non-zero gap should still produce valid audio."""

    from chronovoice.processing.merger import AudioMerger

    segment = _make_segment(tmp_path / "one.wav")
    output = tmp_path / "gap.wav"
    AudioMerger(gap_ms=100, sample_rate=16000).merge([segment], output)
    assert output.is_file()


def test_merger_missing_segment_raises(tmp_path: Path) -> None:
    """A missing segment should raise FileNotFoundError."""

    from chronovoice.processing.merger import AudioMerger

    with pytest.raises(FileNotFoundError):
        AudioMerger().merge([tmp_path / "nope.wav"], tmp_path / "out.wav")