"""Tests for the FastAPI surface using the fake backend.

The API is exercised through FastAPI's TestClient; heavy dependencies
(fastapi, httpx) are required for these tests and skip otherwise.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")  # noqa: F401
from tests.conftest import FakeBackend, make_service, make_wav  # noqa: E402


@pytest.fixture
def api_client(fake_settings, tmp_path):
    """A TestClient bound to a service using a fake backend."""
    from fastapi.testclient import TestClient

    from chronovoice.api.main import create_app
    from chronovoice.api.routes import _get_service

    backend = FakeBackend()
    service = make_service(fake_settings, backend)

    app = create_app()
    app.dependency_overrides[_get_service] = lambda: service
    return TestClient(app)


def test_health(api_client) -> None:
    """The health endpoint should report the fake backend."""
    response = api_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["backend"] == "fake"
    assert payload["loaded"] is False


def test_list_voices(api_client) -> None:
    """The voices endpoint should list registered voices."""
    response = api_client.get("/voices")
    assert response.status_code == 200
    names = [voice["voice_name"] for voice in response.json()]
    assert "daraku" in names


def test_create_voice(api_client, tmp_path) -> None:
    """Creating a voice via the API should succeed."""
    clip = make_wav(tmp_path / "clip.wav")
    payload = {
        "voice_name": "api_voice",
        "reference_audio": str(clip),
        "language": "en",
    }
    response = api_client.post("/voices/create", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["voice_name"] == "api_voice"


def test_tts_json(api_client) -> None:
    """POST /tts should return the output path and chunk count."""
    response = api_client.post("/tts", json={"text": "Hello narration."})
    assert response.status_code == 200
    body = response.json()
    assert body["output_path"]
    assert body["chunk_count"] >= 1


def test_tts_file(api_client) -> None:
    """POST /tts/file should return wav content."""
    response = api_client.post("/tts/file", json={"text": "File narration."})
    assert response.status_code == 200
    assert response.content
    assert response.content[:4] == b"RIFF"


def test_tts_missing_text(api_client) -> None:
    """An empty text payload should be rejected by validation."""
    response = api_client.post("/tts", json={"text": ""})
    assert response.status_code == 422