"""Tests for the synthesis service orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import FakeBackend, make_service
from chronovoice.core.exceptions import VoiceNotFound


def test_synthesize_end_to_end(fake_settings, tmp_path: Path) -> None:
    """Synthesis should produce a merged output file via the fake backend."""
    backend = FakeBackend()
    service = make_service(fake_settings, backend)

    result = service.synthesize("Here's the twist. And another sentence.", output_path=tmp_path / "out.wav")

    assert result.output_path == tmp_path / "out.wav"
    assert result.chunk_count >= 1
    assert result.output_path.is_file()
    assert backend.references  # a voice was cloned
    assert backend.synthesized  # chunks were synthesised


def test_synthesize_respects_configured_voice(fake_settings, tmp_path: Path) -> None:
    """The configured default voice should be cloned."""
    backend = FakeBackend()
    service = make_service(fake_settings, backend)
    service.synthesize("Hello.", output_path=tmp_path / "out.wav")
    reference, language = backend.references[0]
    assert language == "en"
    assert reference.endswith("daraku/reference.wav")


def test_synthesize_unknown_voice_raises(fake_settings, tmp_path: Path) -> None:
    """An unknown voice should surface VoiceNotFound."""
    service = make_service(fake_settings, FakeBackend())
    with pytest.raises(VoiceNotFound):
        service.synthesize("Hello.", voice_name="ghost", output_path=tmp_path / "out.wav")


def test_health_reports_unloaded(fake_settings) -> None:
    """Before any synthesis the backend is reported as unloaded."""
    service = make_service(fake_settings, FakeBackend())
    payload = service.health()
    assert payload["loaded"] is False
    assert payload["backend"] == "fake"


def test_voices_list(fake_settings, voice_library) -> None:
    """The service should expose registered voices."""
    service = make_service(fake_settings, FakeBackend())
    names = [v.voice_name for v in service.voices_list()]
    assert "daraku" in names


def test_pause_and_pronunciation_pipeline(fake_settings, tmp_path: Path) -> None:
    """The pipeline should inject breaks and phonetic spellings."""
    import json

    dict_path = tmp_path / "pronunciations.json"
    dict_path.write_text(json.dumps({"pareidolia": "pa-rye-DOH-lee-ah"}), encoding="utf-8")
    fake_settings.pipeline.pronunciation_path = str(dict_path)

    backend = FakeBackend()
    service = make_service(fake_settings, backend)
    service.synthesize("Pareidolia. Here's the twist.", output_path=tmp_path / "out.wav")

    synthesized_text = " ".join(text for text, _ in backend.synthesized)
    assert "pa-rye-DOH-lee-ah" in synthesized_text
    assert "<break=" in synthesized_text