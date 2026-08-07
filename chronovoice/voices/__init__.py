"""Voice library package: metadata models and management."""

from chronovoice.voices.manager import METADATA_FILENAME, REFERENCE_FILENAME, VoiceManager
from chronovoice.voices.models import VoiceMetadata

__all__ = [
    "VoiceManager",
    "VoiceMetadata",
    "REFERENCE_FILENAME",
    "METADATA_FILENAME",
]