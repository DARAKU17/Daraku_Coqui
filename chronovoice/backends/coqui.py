"""Coqui XTTS v2 backend.

Wraps the ``TTS`` package (XTTS v2) behind :class:`BaseTTSBackend`. Heavy
third-party imports (``torch``, ``TTS``) are deferred to :meth:`load` so the
package imports cleanly even when the optional dependencies are not
installed. This makes the CLI and API usable for introspection while giving
a clear error when synthesis is actually attempted without the backend.
"""

from __future__ import annotations

from pathlib import Path

from chronovoice.backends.base import BaseTTSBackend
from chronovoice.core.exceptions import (
    BackendNotLoaded,
    GenerationFailed,
    UnsupportedLanguage,
)
from chronovoice.core.logger import get_logger

logger = get_logger(__name__)

#: Languages supported out of the box by XTTS v2.
XTTS_LANGUAGES: tuple[str, ...] = (
    "en",
    "es",
    "de",
    "fr",
    "tr",
    "it",
    "pt",
    "pl",
    "nl",
    "ru",
    "ar",
    "zh",
    "hi",
    "ko",
    "ja",
    "cs",
    "hu",
)


class CoquiBackend(BaseTTSBackend):
    """Coqui XTTS v2 implementation of :class:`BaseTTSBackend`.

    Attributes:
        name: Backend identifier ``"coqui"``.
    """

    name: str = "coqui"

    def __init__(self, device: str = "cpu", model_path: str | None = None) -> None:
        """Initialise a Coqui backend in an unloaded state.

        Args:
            device: Compute device, ``"cpu"`` or ``"cuda"``.
            model_path: Optional local path to a pre-trained model.
        """
        super().__init__()
        self._device: str = device
        self._model_path: str | None = model_path
        self._model: object | None = None
        self._current_language: str | None = None
        self._reference: Path | None = None

    @property
    def supports_multilingual(self) -> bool:
        """XTTS v2 speaks many languages.

        Returns:
            ``True``.
        """
        return True

    @property
    def supports_streaming(self) -> bool:
        """Streaming is not exposed yet.

        Returns:
            ``False``.
        """
        return False

    @property
    def supports_voice_cloning(self) -> bool:
        """XTTS v2 clones voices from reference clips.

        Returns:
            ``True``.
        """
        return True

    def load(self) -> None:
        """Load the XTTS v2 model into memory.

        The optional ``TTS`` package is imported lazily here so the rest
        of ChronoVoice works without it installed. A local model path is
        passed through to the model constructor when provided.

        Raises:
            RuntimeError: If the ``TTS`` package is not installed.
        """
        if self._loaded:
            return
        try:
            from TTS.api import TTS  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - depends on env
            raise RuntimeError(
                "The 'TTS' package is not installed. Install it with "
                "'pip install TTS' or the project's 'xtts' extra."
            ) from exc

        self._tts = TTS
        logger.info(
            "Loading Coqui XTTS model",
            extra={"context": {"device": self._device, "model_path": self._model_path}},
        )
        if self._model_path:
            self._model = TTS(model_path=self._model_path)
        else:
            self._model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        self._model.to(self._device)
        self._loaded = True

    def unload(self) -> None:
        """Release the model and clear GPU memory if available.

        Returns:
            None
        """
        if self._loaded:
            self._model = None
            self._current_language = None
            self._reference = None
            self._loaded = False
            logger.info("Unloaded Coqui XTTS backend")
        if self._device == "cuda":
            try:
                import torch  # noqa: PLC0415

                torch.cuda.empty_cache()
            except Exception:  # pragma: no cover - device dependent
                logger.warning("Could not clear CUDA cache on unload")

    def clone_voice(self, reference_audio: Path, language: str) -> None:
        """Store the reference clip the model should clone.

        XTTS clones on the fly during synthesis from the reference wav, so
        this stage records the reference and validates supported language.

        Args:
            reference_audio: Path to the reference audio file.
            language: Language code of the reference.

        Raises:
            BackendNotLoaded: If the model has not been loaded.
            GenerationFailed: If the reference file is missing or unreadable.
            UnsupportedLanguage: If the language is not supported by XTTS.
        """
        self._ensure_loaded()
        if not Path(reference_audio).is_file():
            raise GenerationFailed(f"Reference audio not found: {reference_audio}")
        if language not in XTTS_LANGUAGES:
            raise UnsupportedLanguage(language, XTTS_LANGUAGES)
        self._current_language = language
        self._reference = Path(reference_audio)
        logger.info(
            "Cloned voice prepared",
            extra={"context": {"reference": str(reference_audio), "language": language}},
        )

    def synthesize(self, text: str, output_path: Path | str) -> Path:
        """Synthesise text to audio using the cloned voice.

        Args:
            text: The cleaned text to speak.
            output_path: Destination for the generated wav.

        Returns:
            Resolved path of the generated audio file.

        Raises:
            BackendNotLoaded: If the model is not loaded.
            GenerationFailed: On any synthesis failure.
        """
        self._ensure_loaded()
        if self._reference is None:
            raise BackendNotLoaded("A voice must be cloned before synthesis")
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._model.tts_to_file(
                text=text,
                speaker_wav=str(self._reference),
                language=self._current_language,
                file_path=str(destination),
            )
        except Exception as exc:  # noqa: BLE001 - wrap unexpected failures
            raise GenerationFailed(f"XTTS synthesis failed: {exc}") from exc
        logger.info(
            "Synthesised audio",
            extra={"context": {"output": str(destination)}},
        )
        return destination

    def _ensure_loaded(self) -> None:
        """Raise if the backend has no loaded model.

        Raises:
            BackendNotLoaded: If the model is not currently loaded.
        """
        if not self._loaded or self._model is None:
            raise BackendNotLoaded(
                "Coqui backend is not loaded. Call load() first."
            )