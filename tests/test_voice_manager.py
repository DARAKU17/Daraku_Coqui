"""Tests for voice library management."""

from __future__ import annotations

from pathlib import Path

import pytest

from chronovoice.core.exceptions import InvalidReferenceAudio, VoiceNotFound
from chronovoice.voices.manager import VoiceManager
from chronovoice.voices.models import VoiceMetadata


def _copy_converter(source: Path, target: Path, sample_rate: int, max_seconds: float) -> Path:
    """Fake converter that copies bytes, standing in for pydub/ffmpeg."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target


def _make_manager(library: Path, converter=None) -> VoiceManager:
    """Build a manager over ``library`` with an optional converter."""
    return VoiceManager(library, converter=converter or _copy_converter)


def test_list_finds_voice(voice_library: Path) -> None:
    """The fixture voice should be discovered."""
    manager = _make_manager(voice_library)
    voices = manager.list()
    assert [v.voice_name for v in voices] == ["daraku"]


def test_resolve_known_voice(voice_library: Path) -> None:
    """Resolving a known voice should return its metadata."""
    manager = _make_manager(voice_library)
    voice = manager.resolve("daraku")
    assert isinstance(voice, VoiceMetadata)
    assert voice.language == "en"


def test_resolve_unknown_raises(voice_library: Path) -> None:
    """Resolving an unknown voice should raise VoiceNotFound."""
    manager = _make_manager(voice_library)
    with pytest.raises(VoiceNotFound):
        manager.resolve("ghost")


def test_reference_path(voice_library: Path) -> None:
    """Reference path should point at the wav file."""
    manager = _make_manager(voice_library)
    voice = manager.resolve("daraku")
    reference = manager.reference_path(voice)
    assert reference.name == "reference.wav"
    assert reference.is_file()


def test_create_voice(voice_library: Path, tmp_path: Path) -> None:
    """Creating a voice should convert the clip and write metadata."""
    from tests.conftest import make_wav

    source = make_wav(tmp_path / "clip.wav")
    manager = _make_manager(voice_library)
    created = manager.create("brand_new", source, language="en")

    assert created.voice_name == "brand_new"
    assert (voice_library / "brand_new" / "reference.wav").is_file()
    assert manager.resolve("brand_new").voice_name == "brand_new"


def test_create_uses_converter(voice_library: Path, tmp_path: Path) -> None:
    """The injected converter should be invoked with normalization args."""
    from tests.conftest import make_wav

    calls: list[tuple] = []
    source = make_wav(tmp_path / "clip.wav", sample_rate=22050)

    def recording_converter(src: Path, tgt: Path, rate: int, max_sec: float) -> Path:
        calls.append((src, tgt, rate, max_sec))
        return _copy_converter(src, tgt, rate, max_sec)

    manager = _make_manager(voice_library, converter=recording_converter)
    manager.create("converted", source, language="en", sample_rate=22050)

    assert len(calls) == 1
    _, target, rate, max_sec = calls[0]
    assert rate == 22050
    assert max_sec == 30.0
    assert target.name == "reference.wav"


def test_create_converter_failure(voice_library: Path, tmp_path: Path) -> None:
    """A failing converter should surface as InvalidReferenceAudio."""
    from tests.conftest import make_wav

    source = make_wav(tmp_path / "clip.wav")

    def failing_converter(src: Path, tgt: Path, rate: int, max_sec: float) -> Path:
        raise InvalidReferenceAudio("decode failed")

    manager = _make_manager(voice_library, converter=failing_converter)
    with pytest.raises(InvalidReferenceAudio):
        manager.create("broken", source, language="en")


def test_create_missing_reference(voice_library: Path) -> None:
    """Creating with a missing clip should raise InvalidReferenceAudio."""
    manager = _make_manager(voice_library)
    with pytest.raises(InvalidReferenceAudio):
        manager.create("x", voice_library / "nope.wav")


def test_validate_reference_accepts_wav(voice_library: Path) -> None:
    """A real wav should validate against its voice."""
    from tests.conftest import make_wav

    manager = _make_manager(voice_library)
    voice = VoiceMetadata(voice_name="t", sample_rate=22050)
    wav = make_wav(voice_library / "v" / "reference.wav")
    manager.validate_reference(wav, voice)  # should not raise


def test_validate_reference_rejects_non_wav(voice_library: Path) -> None:
    """A non-wav file should raise InvalidReferenceAudio."""
    manager = _make_manager(voice_library)
    voice = VoiceMetadata(voice_name="t")
    bogus = voice_library / "bogus.wav"
    bogus.write_bytes(b"not a wav file")
    with pytest.raises(InvalidReferenceAudio):
        manager.validate_reference(bogus, voice)


def test_validate_reference_rejects_too_long(voice_library: Path) -> None:
    """A reference longer than the maximum should be rejected."""
    from tests.conftest import make_wav

    manager = _make_manager(voice_library)
    voice = VoiceMetadata(voice_name="t", sample_rate=22050)
    long_wav = make_wav(voice_library / "long" / "reference.wav", seconds=45.0)
    with pytest.raises(InvalidReferenceAudio):
        manager.validate_reference(long_wav, voice)