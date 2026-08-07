"""Application configuration for ChronoVoice.

Settings are modelled with Pydantic and loaded from a YAML file. Values
not present in the YAML file fall back to the defaults defined here so
a minimal ``config.yaml`` works out of the box.

Design notes:
    * The configuration is a single immutable :class:`Settings` instance.
    * ``load_settings`` caches the result so the whole process shares one
      configuration object.
    * Backends, pipeline stages and the service layer all read from the
      same settings object, keeping the system in a single source of truth.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, ClassVar

import yaml
from pydantic import BaseModel, Field, field_validator

from chronovoice.core.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG_NAME: str = "config.yaml"
DEFAULT_OUTPUT_DIR_NAME: str = "output"
DEFAULT_VOICES_DIR_NAME: str = "voices"

#: Standard sample rate for voice cloning reference audio (Hz).
REFERENCE_SAMPLE_RATE: int = 22050
#: Minimum length of a reference clip in seconds.
MIN_REFERENCE_SECONDS: float = 3.0


class BackendSettings(BaseModel):
    """Configuration block describing the active TTS backend.

    Attributes:
        name: Identifier of the backend, e.g. ``coqui``.
        device: Compute device to use, e.g. ``cpu`` or ``cuda``.
        model_path: Optional local path to a pre-trained model.
    """

    name: str = "coqui"
    device: str = "cpu"
    model_path: str | None = None


class PipelineSettings(BaseModel):
    """Configuration block for the text processing pipeline.

    Attributes:
        chunk_size: Maximum number of characters per chunk.
        pause_length: Default pause inserted after rule matches, in ms.
        pronunciation_path: Optional path to a pronunciation dictionary.
    """

    chunk_size: int = Field(default=400, ge=10)
    pause_length: int = Field(default=350, ge=0)
    pronunciation_path: str | None = None


class Settings(BaseModel):
    """Root application settings loaded from YAML.

    Attributes:
        backend: Active backend configuration.
        pipeline: Text processing pipeline configuration.
        language: Default language code used for synthesis.
        voice: Default voice name used for synthesis.
        output_dir: Directory where generated audio is written.
        voices_dir: Directory that holds the voice library.
        sample_rate: Sample rate used for generated audio.
    """

    backend: BackendSettings = BackendSettings()
    pipeline: PipelineSettings = PipelineSettings()
    language: str = "en"
    voice: str = "daraku"
    output_dir: str = DEFAULT_OUTPUT_DIR_NAME
    voices_dir: str = DEFAULT_VOICES_DIR_NAME
    sample_rate: int = Field(default=24000, ge=8000)

    _config_path: ClassVar[Path | None] = None

    @field_validator("output_dir", "voices_dir")
    @classmethod
    def _validate_directories(cls, value: str) -> str:
        """Ensure directory settings are not blank.

        Args:
            value: The configured directory string.

        Returns:
            The unchanged value.

        Raises:
            ValueError: If the value is blank or whitespace only.
        """
        if not value.strip():
            raise ValueError("directory settings must not be empty")
        return value

    def resolved_output_dir(self) -> Path:
        """Resolve the output directory to an absolute path.

        The path is resolved relative to the configuration file location
        when one was loaded, otherwise relative to the current directory.

        Returns:
            Absolute path of the output directory.
        """
        return self._resolve(self.output_dir)

    def resolved_voices_dir(self) -> Path:
        """Resolve the voices directory to an absolute path.

        Returns:
            Absolute path of the voices directory.
        """
        return self._resolve(self.voices_dir)

    def _resolve(self, value: str) -> Path:
        """Resolve a relative path against the config file directory.

        Args:
            value: The configured path value.

        Returns:
            An absolute path.
        """
        base = self._config_path.parent if self._config_path else Path.cwd()
        path = Path(value)
        return path if path.is_absolute() else base / path


class SettingsStore:
    """Loads and caches :class:`Settings` from a YAML file.

    The store performs a lightweight YAML read and merge over the default
    settings, then exposes the immutable result. Loading the same file
    twice returns the cached instance.
    """

    def __init__(self) -> None:
        """Initialize the store with no loaded settings."""
        self._settings: Settings | None = None

    def load(self, path: str | Path | None = None) -> Settings:
        """Load settings from a YAML file, caching the result.

        If ``path`` is not supplied the ``CHRONOVOICE_CONFIG`` environment
        variable is consulted, then a ``config.yaml`` in the current
        directory, then the package default.

        Args:
            path: Optional explicit path to a YAML configuration file.

        Returns:
            The immutable application :class:`Settings`.

        Raises:
            FileNotFoundError: If the resolved config file does not exist.
        """
        if self._settings is not None:
            return self._settings

        config_path = self._resolve_config_path(path)
        data: dict[str, Any] = {}
        if config_path is not None:
            if not config_path.is_file():
                raise FileNotFoundError(f"Config file not found: {config_path}")
            with config_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            Settings._config_path = config_path
            logger.info("Loaded configuration from %s", config_path)

        merged = self._deep_merge(Settings().model_dump(), data)
        self._settings = Settings.model_validate(merged)
        return self._settings

    @staticmethod
    def _resolve_config_path(path: str | Path | None) -> Path | None:
        """Resolve the configuration file path from explicit/env/default.

        Args:
            path: An explicitly supplied path, or ``None``.

        Returns:
            The resolved path, or ``None`` when no default exists.
        """
        if path is not None:
            return Path(path).expanduser().resolve()
        env_path = os.environ.get("CHRONOVOICE_CONFIG")
        if env_path:
            return Path(env_path).expanduser().resolve()
        candidate = Path.cwd() / DEFAULT_CONFIG_NAME
        if candidate.is_file():
            return candidate
        return None

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge ``override`` into ``base``.

        Nested dictionaries are merged key by key so partial YAML configs
        only override the fields they declare.

        Args:
            base: The default dictionary.
            override: The dictionary read from YAML.

        Returns:
            A new merged dictionary.
        """
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = SettingsStore._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged


_store = SettingsStore()


def load_settings(path: str | Path | None = None) -> Settings:
    """Load the application settings (cached per process).

    This is the canonical entry point for reading configuration.

    Args:
        path: Optional explicit path to a YAML configuration file.

    Returns:
        The application :class:`Settings`.
    """
    return _store.load(path)
