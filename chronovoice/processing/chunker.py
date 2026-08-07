"""Splitting narration text into synthesizable chunks.

Chunking keeps each segment short enough for the backend and for accurate
progress reporting. We split on sentence boundaries first, then merge small
sentences up to a target maximum size so the pipeline produces fewer, larger
audio files without exceeding the model's comfortable input length.
"""

from __future__ import annotations

import re

_SENTENCE_SPLIT_RE: re.Pattern[str] = re.compile(r"(?<=[.!?…])\s+")


class SentenceChunker:
    """Split text into chunks of at most ``max_chars`` characters.

    Args:
        max_chars: Maximum characters per returned chunk.
    """

    def __init__(self, max_chars: int = 400) -> None:
        """Initialise the chunker.

        Args:
            max_chars: Maximum characters per chunk (must be positive).
        """
        if max_chars < 1:
            raise ValueError("max_chars must be a positive integer")
        self._max_chars: int = max_chars

    def process(self, text: str) -> list[str]:
        """Split text into a sequence of chunks.

        Args:
            text: The cleaned text to split.

        Returns:
            A list of chunk strings, each at most ``max_chars`` long.
        """
        sentences = [
            part.strip()
            for part in _SENTENCE_SPLIT_RE.split(text)
            if part.strip()
        ]
        return self._merge_sentences(sentences)

    def _merge_sentences(self, sentences: list[str]) -> list[str]:
        """Merge short sentences up to the maximum chunk size.

        Args:
            sentences: Individual sentence strings.

        Returns:
            A list of combined chunks.
        """
        chunks: list[str] = []
        current: str = ""

        for sentence in sentences:
            if len(sentence) > self._max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._split_long_sentence(sentence))
                continue
            if not current:
                current = sentence
            elif len(current) + len(sentence) + 1 <= self._max_chars:
                current = f"{current} {sentence}"
            else:
                chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)
        return chunks

    def _split_long_sentence(self, sentence: str) -> list[str]:
        """Split a single over-long sentence into word-aligned chunks.

        Args:
            sentence: A sentence longer than the maximum chunk size.

        Returns:
            A list of sub-chunks, each at most ``max_chars`` long.
        """
        words = sentence.split()
        chunks: list[str] = []
        current: str = ""
        for word in words:
            if not current:
                current = word
            elif len(current) + len(word) + 1 <= self._max_chars:
                current = f"{current} {word}"
            else:
                chunks.append(current)
                current = word
        if current:
            chunks.append(current)
        return chunks