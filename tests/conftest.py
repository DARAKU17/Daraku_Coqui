"""Shared fixtures and helpers for the test suite.

These tests deliberately avoid the heavy TTS stack: they use fakes and
stdlib-only audio generation so the suite runs anywhere.
"""

from __future__ import annotations

import shutil
import struct
import wave
from pathlib import Path

import pytest

from chronovoice.service.tts_service import TTSService


def make_wav(path: Path, sample_rate: int = 22050, seconds: float = 1.0) -> Path:
    """Write a minimal valid WAV file of silence.

    Args:
        path: Destination path.
        sample_rate: Sample rate in Hz.
        seconds: Duration in seconds.

    Returns:
        The created path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frames)
    return path


@pytest.fixture
def voice_library(tmp_path: Path) -> Path:
    """Create a throwaway voice library with a single valid voice."""
    voice_dir = tmp_path / "voices"
    daraku = voice_dir / "daraku"
    daraku.mkdir(parents=True)
    make_wav(daraku / "reference.wav")
    (daraku / "metadata.json").write_text(
        '{"voice_name": "daraku", "language": "en", "sample_rate": 22050}',
        encoding="utf-8",
    )
    return voice_dir


@pytest.fixture
def fake_settings(tmp_path: Path, voice_library: Path):
    """Settings pointing at a throwaway voice library and output dir."""
    from chronovoice.core.config import Settings

    settings = Settings(
        voice="daraku",
        voices_dir=str(voice_library),
        output_dir=str(tmp_path / "output"),
        sample_rate=24000,
    )
    settings._config_path = None
    return settings


class FakeBackend:
    """In-memory stand-in for BaseTTSBackend used by service tests.

    Records calls instead of touching a real model, and writes a tiny WAV
    to the requested output path so downstream merging works.
    """

    name: str = "fake"

    def __init__(self) -> None:
        """Initialise an unloaded fake backend."""
        self._loaded = False
        self.references: list[tuple[str, str]] = []
        self.synthesized: list[tuple[str, Path]] = []

    def load(self) -> None:
        """Mark the backend as loaded."""
        self._loaded = True

    def unload(self) -> None:
        """Mark the backend as unloaded."""
        self._loaded = False

    def clone_voice(self, reference_audio, language) -> None:
        """Record the cloned reference and language."""
        self.references.append((str(reference_audio), language))

    def synthesize(self, text, output_path) -> Path:
        """Record the synthesis and emit a minimal wav."""
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.synthesized.append((text, destination))
        make_wav(destination, sample_rate=24000)
        return destination

    def is_loaded(self) -> bool:
        """Report the fake load state."""
        return self._loaded

    @property
    def supports_multilingual(self) -> bool:
        """Fake capability flag."""
        return True

    @property
    def supports_streaming(self) -> bool:
        """Fake capability flag."""
        return False

    @property
    def supports_voice_cloning(self) -> bool:
        """Fake capability flag."""
        return True


def make_service(settings, backend: FakeBackend) -> TTSService:
    """Build a TTSService wired to a fake backend.

    Args:
        settings: Settings to use.
        backend: The fake backend instance.

    Returns:
        A configured service.
    """
    settings.backend.name = "fake"
    service = TTSService(settings)
    manager = service._backends
    manager._backend = backend
    manager._backend_name = "fake"
    return service