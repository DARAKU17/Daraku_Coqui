"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from chronovoice.core.config import Settings


def test_defaults() -> None:
    """Defaults should match the documented configuration."""
    settings = Settings()
    assert settings.backend.name == "coqui"
    assert settings.backend.device == "cpu"
    assert settings.pipeline.chunk_size == 400
    assert settings.pipeline.pause_length == 350
    assert settings.sample_rate == 24000


def test_load_from_yaml(tmp_path: Path) -> None:
    """Settings should load from a YAML file."""
    import yaml

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.safe_dump({"language": "es", "sample_rate": 16000}), encoding="utf-8"
    )
    from chronovoice.core.config import SettingsStore

    settings = SettingsStore().load(config_file)
    assert settings.language == "es"
    assert settings.sample_rate == 16000


def test_load_missing_file_raises(tmp_path: Path) -> None:
    """Loading a missing config file should raise FileNotFoundError."""
    from chronovoice.core.config import SettingsStore

    with pytest.raises(FileNotFoundError):
        SettingsStore().load(tmp_path / "missing.yaml")


def test_pipeline_validation() -> None:
    """Negative pause length should be rejected."""
    with pytest.raises(ValueError):
        Settings(pipeline={"pause_length": -1})