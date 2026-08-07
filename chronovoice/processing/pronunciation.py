"""Phonetic pronunciation dictionary.

XTTS can stumble on uncommon proper nouns (pareidolia, Jakobovits,
Mariotte, Titchener). This module maps a written phrase to its phonetic
spelling and rewrites the text before synthesis so the model pronounces
it correctly. Dictionaries are stored as JSON.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_TOKEN_RE: re.Pattern[str] = re.compile(r"[A-Za-z']+|[^A-Za-z']+")


class PronunciationDictionary:
    """Case-insensitive phrase-to-phonetic dictionary.

    Args:
        entries: Optional mapping of phrase to phonetic replacement.
    """

    def __init__(self, entries: dict[str, str] | None = None) -> None:
        """Initialise the dictionary.

        Args:
            entries: Optional initial mapping of phrase to phonetic spelling.
        """
        self._entries: dict[str, str] = {
            phrase.lower(): phonetic
            for phrase, phonetic in (entries or {}).items()
        }

    @classmethod
    def from_json(cls, path: str | Path) -> "PronunciationDictionary":
        """Load a dictionary from a JSON file.

        The file is a flat mapping::

            {
                "pareidolia": "pa-rye-DOH-lee-ah",
                "Titchener": "TITCH-ner"
            }

        Args:
            path: Path to the JSON dictionary.

        Returns:
            A populated :class:`PronunciationDictionary`.

        Raises:
            FileNotFoundError: If the dictionary file does not exist.
            ValueError: If the JSON root is not a mapping of strings.
        """
        dict_path = Path(path)
        if not dict_path.is_file():
            raise FileNotFoundError(f"Pronunciation dictionary not found: {dict_path}")
        with dict_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError("Pronunciation dictionary JSON must be an object")
        entries = {str(k): str(v) for k, v in raw.items()}
        return cls(entries=entries)

    def add(self, phrase: str, phonetic: str) -> None:
        """Add or update a single entry.

        Args:
            phrase: The written phrase to override.
            phonetic: The phonetic spelling the model should use.
        """
        self._entries[phrase.lower()] = phonetic

    def process(self, text: str) -> str:
        """Rewrite known phrases to their phonetic spellings.

        Substitution is token aware: each phrase is looked up by exact token
        sequence (case-insensitive), so partial words are never mangled.

        Args:
            text: Text to process before synthesis.

        Returns:
            The text with known phrases phonetically replaced.
        """
        if not self._entries:
            return text
        tokens = _TOKEN_RE.findall(text)
        for index, token in enumerate(tokens):
            if token.isalpha() and token.lower() in self._entries:
                tokens[index] = self._entries[token.lower()]
        return "".join(tokens)