"""Text processing pipeline stages.

Each module in this package is independent and exposes a ``process()``
method, allowing stages to be reordered or extended without touching the
rest of the codebase.
"""

from chronovoice.processing.chunker import SentenceChunker
from chronovoice.processing.cleaner import TextCleaner
from chronovoice.processing.merger import AudioMerger
from chronovoice.processing.pauses import PauseInjector, PauseRule
from chronovoice.processing.pronunciation import PronunciationDictionary

__all__ = [
    "TextCleaner",
    "SentenceChunker",
    "PauseInjector",
    "PauseRule",
    "PronunciationDictionary",
    "AudioMerger",
]