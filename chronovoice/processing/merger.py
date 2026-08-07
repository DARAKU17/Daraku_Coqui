"""Merging per-chunk audio files into a single narration.

Audio synthesis is performed chunk by chunk; the merger stitches the
resulting wav files into one normalized file, inserting an optional silence
gap between them for natural pacing.
"""

from __future__ import annotations

from pathlib import Path

from chronovoice.core.logger import get_logger

logger = get_logger(__name__)


class AudioMerger:
    """Concatenate wav segments into a single output file.

    Merging requires the ``pydub`` library; the import is deferred so the
    rest of the package works without it.

    Args:
        gap_ms: Silence inserted between segments, in milliseconds.
        sample_rate: Target sample rate for the merged output.
    """

    def __init__(self, gap_ms: int = 350, sample_rate: int = 24000) -> None:
        """Initialise the merger.

        Args:
            gap_ms: Silence inserted between segments, in milliseconds.
            sample_rate: Target sample rate of the merged audio.
        """
        self._gap_ms: int = gap_ms
        self._sample_rate: int = sample_rate

    def merge(self, segments: list[Path] | list[str], output_path: Path | str) -> Path:
        """Merge segment files into ``output_path``.

        Args:
            segments: Ordered paths of wav segment files.
            output_path: Destination for the merged file.

        Returns:
            Resolved path of the merged file.

        Raises:
            FileNotFoundError: If a segment file does not exist.
        """
        from pydub import AudioSegment  # noqa: PLC0415

        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        combined: AudioSegment | None = None
        for segment in segments:
            segment_path = Path(segment)
            if not segment_path.is_file():
                raise FileNotFoundError(f"Segment not found: {segment_path}")
            audio = AudioSegment.from_file(segment_path)
            if combined is None:
                combined = audio
            else:
                if self._gap_ms:
                    combined += AudioSegment.silent(duration=self._gap_ms)
                combined += audio

        if combined is None:
            raise ValueError("No audio segments were supplied to merge")

        combined = combined.set_frame_rate(self._sample_rate)
        combined.export(destination, format="wav")
        logger.info(
            "Merged %d segments into %s", len(segments), destination
        )
        return destination