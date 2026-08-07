"""Tests for the text cleaning stage."""

from __future__ import annotations

from chronovoice.processing.cleaner import TextCleaner


def test_collapses_whitespace() -> None:
    """Runs of whitespace should collapse to a single space."""
    cleaner = TextCleaner()
    assert cleaner.process("Hello\n\nworld\t!") == "Hello world!"


def test_removes_space_before_punctuation() -> None:
    """A space before terminal punctuation should be removed."""
    cleaner = TextCleaner()
    assert cleaner.process("Hello world .") == "Hello world."


def test_normalizes_duplicate_terminals() -> None:
    """Repeated terminal punctuation should collapse to one mark."""
    cleaner = TextCleaner()
    assert cleaner.process("What?!?!") == "What?"


def test_strips_surrounding_whitespace() -> None:
    """Surrounding whitespace should be stripped."""
    cleaner = TextCleaner()
    assert cleaner.process("   hello   ") == "hello"


def test_preserves_inner_punctuation() -> None:
    """Normal punctuation inside sentences must be kept."""
    cleaner = TextCleaner()
    result = cleaner.process("It's a test; it works, doesn't it?")
    assert result == "It's a test; it works, doesn't it?"