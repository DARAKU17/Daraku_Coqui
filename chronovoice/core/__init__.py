"""Core package: configuration, logging and exceptions.

``core.config`` requires pydantic; it is exposed lazily so importing the
package's logging/exceptions alone works without third-party dependencies.
"""

from __future__ import annotations

from typing import Any

from chronovoice.core.constants import (
    MAX_REFERENCE_SECONDS,
    MIN_REFERENCE_SECONDS,
    REFERENCE_SAMPLE_RATE,
)
from chronovoice.core.exceptions import (
    BackendNotLoaded,
    ChronoVoiceError,
    GenerationFailed,
    InvalidReferenceAudio,
    UnsupportedLanguage,
    VoiceNotFound,
)


def __getattr__(name: str) -> Any:
    """Lazily resolve pydantic-backed public attributes.

    Args:
        name: The requested attribute name.

    Returns:
        The resolved object.

    Raises:
        AttributeError: If the attribute is unknown.
    """
    if name in ("Settings", "load_settings"):
        from chronovoice.core.config import Settings, load_settings

        return {"Settings": Settings, "load_settings": load_settings}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Settings",
    "load_settings",
    "ChronoVoiceError",
    "BackendNotLoaded",
    "VoiceNotFound",
    "InvalidReferenceAudio",
    "UnsupportedLanguage",
    "GenerationFailed",
    "REFERENCE_SAMPLE_RATE",
    "MIN_REFERENCE_SECONDS",
    "MAX_REFERENCE_SECONDS",
]