"""Tests for the pronunciation dictionary."""

from __future__ import annotations

from chronovoice.processing.pronunciation import PronunciationDictionary

ENTRIES: dict[str, str] = {
    "pareidolia": "pa-rye-DOH-lee-ah",
    "titchener": "TITCH-ner",
    "Jakobovits": "YAH-koh-boh-vits",
}


def test_replaces_known_word() -> None:
    """A known word should be replaced by its phonetic spelling."""
    dictionary = PronunciationDictionary(entries=ENTRIES)
    assert dictionary.process("Pareidolia is common.") == "pa-rye-DOH-lee-ah is common."


def test_case_insensitive_lookup() -> None:
    """Lookup should ignore case in the input text."""
    dictionary = PronunciationDictionary(entries=ENTRIES)
    assert dictionary.process("TITCHENER") == "TITCH-ner"


def test_unknown_words_unchanged() -> None:
    """Words not in the dictionary must pass through untouched."""
    dictionary = PronunciationDictionary(entries=ENTRIES)
    assert dictionary.process("hello world") == "hello world"


def test_empty_dictionary_is_noop() -> None:
    """An empty dictionary should not alter text."""
    dictionary = PronunciationDictionary(entries={})
    assert dictionary.process("pareidolia") == "pareidolia"


def test_partial_words_not_mangled() -> None:
    """Substrings of a known word must not be replaced."""
    dictionary = PronunciationDictionary(entries={"ate": "eigh-t"})
    assert dictionary.process("created state") == "created state"


def test_from_json(tmp_path) -> None:
    """A dictionary should load from a JSON file."""
    import json

    path = tmp_path / "dict.json"
    path.write_text(json.dumps(ENTRIES), encoding="utf-8")
    dictionary = PronunciationDictionary.from_json(path)
    assert dictionary.process("Jakobovits") == "YAH-koh-boh-vits"


def test_add_method() -> None:
    """Entries can be added at runtime."""
    dictionary = PronunciationDictionary()
    dictionary.add("Mariotte", "mah-ree-OT")
    assert dictionary.process("Mariotte") == "mah-ree-OT"