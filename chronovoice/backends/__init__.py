"""Backend registry and factory.

New backends are added by authoring a subclass of :class:`BaseTTSBackend`
that declares a ``name`` and appending it to the registry below. No other
code has to change, which keeps the system open for extension.
"""

from __future__ import annotations

from chronovoice.backends.base import BaseTTSBackend
from chronovoice.backends.coqui import CoquiBackend
from chronovoice.core.exceptions import ChronoVoiceError

#: Maps backend identifier to its implementation class.
BACKEND_REGISTRY: dict[str, type[BaseTTSBackend]] = {
    CoquiBackend.name: CoquiBackend,
}


def register_backend(backend_class: type[BaseTTSBackend]) -> None:
    """Register a backend class under its ``name``.

    Args:
        backend_class: A concrete ``BaseTTSBackend`` subclass.

    Raises:
        ChronoVoiceError: If no name is declared for the backend.
    """
    if not backend_class.name or backend_class.name == "base":
        raise ChronoVoiceError(
            f"Backend '{backend_class.__name__}' must declare a non-empty name"
        )
    BACKEND_REGISTRY[backend_class.name] = backend_class


def create_backend(name: str, **kwargs: object) -> BaseTTSBackend:
    """Instantiate a backend by name.

    Args:
        name: Backend identifier from the configuration.
        **kwargs: Constructor arguments forwarded to the backend.

    Returns:
        An instance of the requested backend.

    Raises:
        ChronoVoiceError: If the backend name is not registered.
    """
    backend_class = BACKEND_REGISTRY.get(name)
    if backend_class is None:
        available = ", ".join(sorted(BACKEND_REGISTRY))
        raise ChronoVoiceError(
            f"Unknown backend '{name}'. Available backends: {available}"
        )
    return backend_class(**kwargs)


def available_backends() -> tuple[str, ...]:
    """List the registered backend identifiers.

    Returns:
        A tuple of backend names.
    """
    return tuple(sorted(BACKEND_REGISTRY))


__all__ = [
    "BaseTTSBackend",
    "BACKEND_REGISTRY",
    "create_backend",
    "available_backends",
    "register_backend",
]