"""Text normalization utilities for narration input.

The cleaner collapses whitespace, normalizes common punctuation and fixes
spacing issues so downstream stages receive predictable text. It is a pure
function of its input and has no dependencies beyond the standard library.
"""

from __future__ import annotations

import re

#: Collapse runs of whitespace (including newlines/tabs) down to a space.
_WHITESPACE_RE: re.Pattern[str] = re.compile(r"\s+")
#: Remove leading space before terminal punctuation such as ``. ! ? ,``.
_SPACE_BEFORE_PUNCT_RE: re.Pattern[str] = re.compile(r"\s+([.,!?;:])")
#: Collapse a run of terminal punctuation (``.``, ``!``, ``?``) to one mark.
_TERMINAL_RUN_RE: re.Pattern[str] = re.compile(r"([.!?])[.!?]+")


class TextCleaner:
    """Cleans and normalizes raw text before chunking and synthesis.

    Processing is intentionally conservative: we only touch whitespace and
    punctuation so meaning and wording are preserved.
    """

    def process(self, text: str) -> str:
        """Clean the supplied text.

        Args:
            text: Raw input text.

        Returns:
            The normalized text with collapsed whitespace and tidy
            punctuation.
        """
        text = _WHITESPACE_RE.sub(" ", text)
        text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
        text = _TERMINAL_RUN_RE.sub(r"\1", text)
        return text.strip()