"""Tests for voice library management."""

from __future__ import annotations

from pathlib import Path

import pytest

from chronovoice.core.exceptions import InvalidReferenceAudio, VoiceNotFound
from chronovoice.voices.manager import VoiceManager
from chronovoice.voices.models import VoiceMetadata


def test_list_finds_voice(voice_library: Path) -> None:
    """The fixture voice should be discovered."""
    manager = VoiceManager(voice_library)
    voices = manager.list()
    assert [v.voice_name for v in voices] == ["daraku"]


def test_resolve_known_voice(voice_library: Path) -> None:
    """Resolving a known voice should return its metadata."""
    manager = VoiceManager(voice_library)
    voice = manager.resolve("daraku")
    assert isinstance(voice, VoiceMetadata)
    assert voice.language == "en"


def test_resolve_unknown_raises(voice_library: Path) -> None:
    """Resolving an unknown voice should raise VoiceNotFound."""
    manager = VoiceManager(voice_library)
    with pytest.raises(VoiceNotFound):
        manager.resolve("ghost")


def test_reference_path(voice_library: Path) -> None:
    """Reference path should point at the wav file."""
    manager = VoiceManager(voice_library)
    voice = manager.resolve("daraku")
    reference = manager.reference_path(voice)
    assert reference.name == "reference.wav"
    assert reference.is_file()


def test_create_voice(voice_library: Path, tmp_path: Path) -> None:
    """Creating a voice should copy the clip and write metadata."""
    from tests.conftest import make_wav

    source = make_wav(tmp_path / "clip.wav")
    manager = VoiceManager(voice_library)
    created = manager.create("brand_new", source, language="en")

    assert created.voice_name == "brand_new"
    assert (voice_library / "brand_new" / "reference.wav").is_file()
    assert manager.resolve("brand_new").voice_name == "brand_new"


def test_create_missing_reference(voice_library: Path) -> None:
    """Creating with a missing clip should raise InvalidReferenceAudio."""
    manager = VoiceManager(voice_library)
    with pytest.raises(InvalidReferenceAudio):
        manager.create("x", voice_library / "nope.wav")


def test_validate_reference_accepts_wav(voice_library: Path) -> None:
    """A real wav should validate against its voice."""
    from tests.conftest import make_wav

    manager = VoiceManager(voice_library)
    voice = VoiceMetadata(voice_name="t", sample_rate=22050)
    wav = make_wav(voice_library / "v" / "reference.wav")
    manager.validate_reference(wav, voice)  # should not raise


def test_validate_reference_rejects_non_wav(voice_library: Path) -> None:
    """A non-wav file should raise InvalidReferenceAudio."""
    manager = VoiceManager(voice_library)
    voice = VoiceMetadata(voice_name="t")
    bogus = voice_library / "bogus.wav"
    bogus.write_bytes(b"not a wav file")
    with pytest.raises(InvalidReferenceAudio):
        manager.validate_reference(bogus, voice)