"""Abstract backend interface for text-to-speech engines.

All TTS providers implement :class:`BaseTTSBackend`. The interface is the
only contract the service layer, API and CLI rely on, which means adding a
new provider only requires authoring a new subclass and registering it in
the backend registry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseTTSBackend(ABC):
    """Abstract contract implemented by every TTS provider.

    Subclasses declare a ``name`` so the registry can map identifier to
    implementation, and implement the lifecycle and synthesis methods below.

    Attributes:
        name: Stable identifier used to select the backend.
    """

    name: str = "base"

    def __init__(self) -> None:
        """Initialise the backend in an unloaded state."""
        self._loaded: bool = False

    @abstractmethod
    def load(self) -> None:
        """Load the underlying model into memory.

        Loading is intentionally separate from cloning so a backend can be
        prepared once and used for many voices. Implementations should raise
        a clear error if the model cannot be initialised.
        """

    @abstractmethod
    def unload(self) -> None:
        """Release the model and any device resources.

        After this call the backend is in an unloaded state and must be
        loaded again before synthesis.
        """

    @abstractmethod
    def clone_voice(self, reference_audio: Path, language: str) -> None:
        """Prepare a cloned voice from a reference clip.

        Args:
            reference_audio: Path to the reference audio file.
            language: Language code of the reference audio.
        """

    @abstractmethod
    def synthesize(self, text: str, output_path: Path | str) -> Path:
        """Generate speech for a single text passage.

        Args:
            text: The text to synthesise.
            output_path: Where the generated audio should be written.

        Returns:
            The path of the generated audio file.
        """

    @property
    @abstractmethod
    def supports_multilingual(self) -> bool:
        """Whether the backend can speak multiple languages."""

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether the backend can stream audio as it is generated."""

    @property
    @abstractmethod
    def supports_voice_cloning(self) -> bool:
        """Whether the backend can clone voices from a reference clip."""

    def is_loaded(self) -> bool:
        """Report whether the backend currently has a loaded model.

        Returns:
            ``True`` when a model is resident, otherwise ``False``.
        """
        return self._loaded