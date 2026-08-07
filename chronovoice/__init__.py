"""ChronoVoice — a local AI narration toolkit built on Coqui XTTS v2.

Importing ``chronovoice`` has no side effects and requires no third-party
dependencies: heavy libraries (``torch``, ``TTS``, ``fastapi``, ``pydantic``)
are only imported when the relevant submodule is used. Public helpers are
exposed lazily through module ``__getattr__`` (PEP 562).
"""

from __future__ import annotations

from typing import Any

__version__: str = "0.1.0"


def __getattr__(name: str) -> Any:
    """Lazily resolve a public attribute.

    Args:
        name: The requested attribute name.

    Returns:
        The resolved object.

    Raises:
        AttributeError: If the attribute is unknown.
    """
    if name == "load_settings":
        from chronovoice.core import load_settings

        return load_settings
    if name == "TTSService":
        from chronovoice.service import TTSService

        return TTSService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["__version__"]