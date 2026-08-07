"""Voice library management.

A voice is a directory containing ``reference.wav`` and ``metadata.json``.
The manager scans the voices directory, validates reference audio, and
resolves voices by name for the rest of the application.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

from chronovoice.core.exceptions import InvalidReferenceAudio, VoiceNotFound
from chronovoice.core.logger import get_logger
from chronovoice.voices.models import VoiceMetadata

logger = get_logger(__name__)

#: Standard name of the reference audio file within a voice directory.
REFERENCE_FILENAME: str = "reference.wav"
#: Standard name of the metadata file within a voice directory.
METADATA_FILENAME: str = "metadata.json"


class VoiceManager:
    """Discovers and manages voices inside a directory.

    Args:
        voices_dir: Root directory that contains one subdirectory per voice.
    """

    def __init__(self, voices_dir: str | Path) -> None:
        """Initialise the manager with a voices directory.

        Args:
            voices_dir: Directory containing voice subdirectories.
        """
        self._voices_dir: Path = Path(voices_dir)
        self._cache: dict[str, VoiceMetadata] | None = None

    def list(self, force_reload: bool = False) -> list[VoiceMetadata]:
        """List all registered voices.

        Args:
            force_reload: Rescan the directory instead of using the cache.

        Returns:
            A list of validated :class:`VoiceMetadata` objects.
        """
        if self._cache is None or force_reload:
            self._cache = self._scan()
        return list(self._cache.values())

    def resolve(self, voice_name: str) -> VoiceMetadata:
        """Resolve a voice by name.

        Args:
            voice_name: The voice to look up.

        Returns:
            The matching :class:`VoiceMetadata`.

        Raises:
            VoiceNotFound: If no such voice is registered.
        """
        voices = self.list()
        for voice in voices:
            if voice.voice_name == voice_name.lower():
                return voice
        raise VoiceNotFound(voice_name)

    def reference_path(self, voice: VoiceMetadata) -> Path:
        """Return the absolute path of a voice's reference audio.

        Args:
            voice: The voice metadata.

        Returns:
            The reference audio file path.
        """
        return self._voices_dir / voice.voice_name / REFERENCE_FILENAME

    def create(
        self,
        voice_name: str,
        reference_audio: str | Path,
        language: str = "en",
        description: str = "",
        sample_rate: int = 22050,
    ) -> VoiceMetadata:
        """Register a new voice from a reference clip and target directory.

        Args:
            voice_name: Name of the new voice.
            reference_audio: Source audio clip to copy for the voice.
            language: Language code of the clip.
            description: Optional human readable description.
            sample_rate: Sample rate of the provided clip.

        Returns:
            The new :class:`VoiceMetadata`.

        Raises:
            InvalidReferenceAudio: If the source clip is missing.
        """
        source = Path(reference_audio)
        if not source.is_file():
            raise InvalidReferenceAudio(f"Reference audio not found: {source}")

        voice_dir = self._voices_dir / voice_name.lower()
        voice_dir.mkdir(parents=True, exist_ok=True)
        target = voice_dir / REFERENCE_FILENAME
        target.write_bytes(source.read_bytes())

        metadata = VoiceMetadata(
            voice_name=voice_name,
            language=language,
            description=description,
            sample_rate=sample_rate,
        )
        self._write_metadata(voice_dir, metadata)
        self._cache = None
        logger.info(
            "Created voice '%s'", metadata.voice_name,
            extra={"context": {"voice_dir": str(voice_dir)}},
        )
        return metadata

    def validate_reference(self, reference: Path, voice: VoiceMetadata) -> None:
        """Validate a reference audio file against its voice metadata.

        Args:
            reference: Path to the reference wav.
            voice: The voice the reference belongs to.

        Raises:
            InvalidReferenceAudio: If the file is missing, unreadable, or
                has the wrong format or sample rate.
        """
        if not reference.is_file():
            raise InvalidReferenceAudio(f"Reference audio not found: {reference}")
        try:
            header = reference.read_bytes()[:44]
        except (OSError, PermissionError) as exc:  # noqa: PERF203
            raise InvalidReferenceAudio(f"Could not read reference audio: {reference}") from exc

        if not header or header[:4] != b"RIFF":
            raise InvalidReferenceAudio(
                f"Reference audio is not a RIFF/WAV file: {reference}"
            )
        actual_rate = self._extract_sample_rate(header)
        if actual_rate and actual_rate != voice.sample_rate:
            logger.warning(
                "Voice '%s' reference sample rate %d differs from metadata %d",
                voice.voice_name,
                actual_rate,
                voice.sample_rate,
            )

    @staticmethod
    def _extract_sample_rate(bytes_audio: bytes) -> int:
        """Extract the sample rate stored in a WAV header.

        Args:
            bytes_audio: Raw WAV bytes with a standard 44-byte header.

        Returns:
            The sample rate in Hz, or 0 if it cannot be determined.
        """
        if len(bytes_audio) < 44 or bytes_audio[:4] != b"RIFF":
            return 0
        # Sample rate lives at byte offset 24 (4 bytes little-endian).
        return struct.unpack("<I", bytes_audio[24:28])[0]

    def _scan(self) -> dict[str, VoiceMetadata]:
        """Scan the voices directory for valid voices.

        Returns:
            Mapping of voice name to metadata.

        Raises:
            FileNotFoundError: If the voices directory does not exist.
        """
        if not self._voices_dir.is_dir():
            raise FileNotFoundError(
                f"Voices directory not found: {self._voices_dir}"
            )
        found: dict[str, VoiceMetadata] = {}
        for entry in sorted(self._voices_dir.iterdir()):
            if not entry.is_dir():
                continue
            metadata_path = entry / METADATA_FILENAME
            if not metadata_path.is_file():
                logger.warning("Voice dir %s has no metadata.json", entry.name)
                continue
            try:
                with metadata_path.open("r", encoding="utf-8") as handle:
                    metadata = VoiceMetadata.model_validate(json.load(handle))
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("Invalid metadata for %s: %s", entry.name, exc)
                continue
            found[metadata.voice_name] = metadata
        return found

    @staticmethod
    def _write_metadata(voice_dir: Path, metadata: VoiceMetadata) -> None:
        """Write voice metadata to ``metadata.json``.

        Args:
            voice_dir: The voice's directory.
            metadata: The metadata to persist.
        """
        path = voice_dir / METADATA_FILENAME
        payload = metadata.model_dump(mode="json")
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")