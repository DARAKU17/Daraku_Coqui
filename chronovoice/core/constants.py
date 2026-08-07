"""Pure constants shared across ChronoVoice.

This module intentionally has no third-party imports so it can be used by
any component (including dependency-light ones) without pulling in pydantic.
"""

#: Standard sample rate for voice cloning reference audio (Hz).
REFERENCE_SAMPLE_RATE: int = 22050
#: Minimum length of a reference clip in seconds.
MIN_REFERENCE_SECONDS: float = 3.0
#: Maximum duration kept when normalizing a reference clip (seconds).
MAX_REFERENCE_SECONDS: float = 30.0

__all__ = [
    "REFERENCE_SAMPLE_RATE",
    "MIN_REFERENCE_SECONDS",
    "MAX_REFERENCE_SECONDS",
]