"""Synthesis service orchestrating backends and the processing pipeline.

The service is the single entry point used by both the API and the CLI so
generation logic is never duplicated. It wires configuration, voice
management, text processing and the TTS backend into a small number of
public operations.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path

from chronovoice.backends import BaseTTSBackend, create_backend
from chronovoice.core.config import Settings, load_settings
from chronovoice.core.exceptions import BackendNotLoaded, GenerationFailed
from chronovoice.core.logger import get_logger
from chronovoice.processing.chunker import SentenceChunker
from chronovoice.processing.cleaner import TextCleaner
from chronovoice.processing.merger import AudioMerger
from chronovoice.processing.pauses import PauseInjector
from chronovoice.processing.pronunciation import PronunciationDictionary
from chronovoice.voices.manager import VoiceManager
from chronovoice.voices.models import VoiceMetadata

logger = get_logger(__name__)

#: Default pauses injected after rhetorical phrases.
DEFAULT_PAUSE_RULES: list[tuple[str, int]] = [
    (r"Sounds impossible\?", 350),
    (r"Here's the twist\.", 350),
    (r"Imagine\.\.\.", 500),
    (r"Congratulations\.", 400),
    (r"\bWait\.", 350),
]


@dataclass(frozen=True)
class SynthesisResult:
    """Result of a narration generation request.

    Attributes:
        output_path: Path of the merged audio file.
        chunk_count: Number of segments synthesised and merged.
    """

    output_path: Path
    chunk_count: int


class TTSBackendManager:
    """Lazy holder for the active TTS backend.

    The manager owns the lifecycle of the configured backend so the service
    can request a loaded, voice-cloned instance on demand.

    Args:
        settings: Application settings used to construct the backend.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialise the manager with application settings.

        Args:
            settings: The application settings.
        """
        self._settings: Settings = settings
        self._backend: BaseTTSBackend | None = None
        self._backend_name: str | None = None

    def backend(self) -> BaseTTSBackend:
        """Return the configured backend, loading it on first use.

        Returns:
            A loaded backend instance.

        Raises:
            ChronoVoiceError: If the configured backend is unknown.
        """
        settings = self._settings.backend
        if self._backend is None or self._backend_name != settings.name:
            self._backend = create_backend(
                settings.name,
                device=settings.device,
                model_path=settings.model_path,
            )
            self._backend_name = settings.name
        if not self._backend.is_loaded():
            self._backend.load()
        return self._backend

    def unload(self) -> None:
        """Unload the active backend, if any."""
        if self._backend is not None and self._backend.is_loaded():
            self._backend.unload()

    def current(self) -> BaseTTSBackend | None:
        """Return the backend instance without forcing a load.

        Returns:
            The currently constructed backend, or ``None`` if none has been
            created yet.
        """
        return self._backend


class TTSService:
    """Facade that exposes high-level narration operations.

    Args:
        settings: Application settings. Defaults to the loaded process
            settings when not provided.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialise the service.

        Args:
            settings: Optional application settings; falls back to the
                globally loaded settings.
        """
        self._settings: Settings = settings or load_settings()
        self._backends: TTSBackendManager = TTSBackendManager(self._settings)
        self._voices: VoiceManager = VoiceManager(self._settings.resolved_voices_dir())

    @property
    def backends(self) -> TTSBackendManager:
        """The backend lifecycle manager.

        Returns:
            The :class:`TTSBackendManager` used by this service.
        """
        return self._backends

    def health(self) -> dict[str, object]:
        """Describe the state of the service.

        Returns:
            A dictionary with backend capability and load state.
        """
        backend = self._backends.current()
        if backend is None:
            return {"backend": self._settings.backend.name, "loaded": False}
        return {
            "backend": backend.name,
            "loaded": backend.is_loaded(),
            "supports_multilingual": backend.supports_multilingual,
            "supports_streaming": backend.supports_streaming,
            "supports_voice_cloning": backend.supports_voice_cloning,
        }

    def synthesize(self, text: str, voice_name: str | None = None, output_path: str | Path | None = None) -> SynthesisResult:
        """Generate a narration file for ``text`` in a cloned voice.

        Args:
            text: The narration text.
            voice_name: Voice to clone, defaults to the configured voice.
            output_path: Destination file, defaults to a timestamped name in
                the configured output directory.

        Returns:
            A :class:`SynthesisResult` describing the output.

        Raises:
            VoiceNotFound: If the requested voice is not registered.
            BackendNotLoaded: If the backend cannot be prepared.
            GenerationFailed: If synthesis fails.
        """
        voice = self._voices.resolve(voice_name or self._settings.voice)
        reference = self._voices.reference_path(voice)
        self._prepare_backend(reference, voice)

        chunks = self._process_text(text)
        destination = self._resolve_output_path(output_path)
        audio_paths: list[Path] = []
        for index, chunk in enumerate(chunks):
            chunk_path = self._settings.resolved_output_dir() / f"_chunk_{index:03d}.wav"
            self._backends.backend().synthesize(chunk, chunk_path)
            audio_paths.append(chunk_path)

        merger = AudioMerger(
            gap_ms=self._settings.pipeline.pause_length,
            sample_rate=self._settings.sample_rate,
        )
        merged = merger.merge(audio_paths, destination)
        return SynthesisResult(output_path=merged, chunk_count=len(chunks))

    def _process_text(self, text: str) -> list[str]:
        """Run the text processing pipeline.

        Args:
            text: The raw input text.

        Returns:
            A list of cleaned, chunked, punctuated passages.
        """
        cleaner = TextCleaner()
        chunker = SentenceChunker(max_chars=self._settings.pipeline.chunk_size)
        injector = PauseInjector(rules=DEFAULT_PAUSE_RULES, default_pause_ms=self._settings.pipeline.pause_length)
        pronunciation = PronunciationDictionary()
        pronunciation_path = self._settings.pipeline.pronunciation_path
        if pronunciation_path:
            pronunciation = PronunciationDictionary.from_json(pronunciation_path)

        cleaned = cleaner.process(text)
        chunks = chunker.process(cleaned)
        return [pronunciation.process(injector.process(chunk)) for chunk in chunks]

    def voices_list(self) -> list[VoiceMetadata]:
        """List the registered voices.

        Returns:
            A list of :class:`VoiceMetadata` objects.
        """
        return self._voices.list()

    def voice_create(
        self,
        voice_name: str,
        reference_audio: str | Path,
        language: str = "en",
        description: str = "",
        sample_rate: int = 22050,
    ) -> VoiceMetadata:
        """Register a new voice with the library.

        Args:
            voice_name: Name of the new voice.
            reference_audio: Source clip to use as a reference.
            language: Language code of the clip.
            description: Optional human readable description.
            sample_rate: Sample rate of the clip in Hz.

        Returns:
            The new :class:`VoiceMetadata`.
        """
        return self._voices.create(
            voice_name=voice_name,
            reference_audio=reference_audio,
            language=language,
            description=description,
            sample_rate=sample_rate,
        )

    def _prepare_backend(self, reference: Path, voice: VoiceMetadata) -> None:
        """Ensure the backend is loaded and cloned for ``voice``.

        Args:
            reference: Path to the reference audio.
            voice: The voice metadata.

        Raises:
            GenerationFailed: If reference audio is unusable.
        """
        backend = self._backends.backend()
        if not backend.supports_voice_cloning:
            raise GenerationFailed(
                f"Backend '{backend.name}' does not support voice cloning"
            )
        backend.clone_voice(reference_audio=reference, language=voice.language)

    def _resolve_output_path(self, output_path: str | Path | None) -> Path:
        """Resolve the output destination.

        Args:
            output_path: Explicit output path or ``None``.

        Returns:
            The resolved output path.
        """
        if output_path is not None:
            return Path(output_path).expanduser().resolve()
        directory = self._settings.resolved_output_dir()
        directory.mkdir(parents=True, exist_ok=True)

        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return directory / f"narration_{stamp}.wav"


_default_service: TTSService | None = None


def get_default_service() -> TTSService:
    """Return a process-wide shared synthesis service.

    The service is created lazily on first access so importing the package
    has no side effects and no models are loaded.

    Returns:
        The shared :class:`TTSService` instance.
    """
    global _default_service
    if _default_service is None:
        _default_service = TTSService()
    return _default_service