"""Tests for the sentence chunking stage."""

from __future__ import annotations

from chronovoice.processing.chunker import SentenceChunker


def test_splits_on_sentence_boundaries() -> None:
    """Single sentences should be returned intact."""
    chunker = SentenceChunker(max_chars=400)
    assert chunker.process("One sentence.") == ["One sentence."]


def test_merges_short_sentences() -> None:
    """Short sentences should combine into one chunk under the limit."""
    chunker = SentenceChunker(max_chars=400)
    result = chunker.process("Hi there. How are you? Good.")
    assert len(result) == 1
    assert result[0] == "Hi there. How are you? Good."


def test_splits_long_input() -> None:
    """Long input should produce multiple chunks."""
    chunker = SentenceChunker(max_chars=20)
    text = "This is a very long sentence indeed. And another one here."
    result = chunker.process(text)
    assert len(result) > 1
    assert all(len(chunk) <= 20 for chunk in result)


def test_respects_max_chars() -> None:
    """No chunk should exceed the configured maximum."""
    chunker = SentenceChunker(max_chars=30)
    text = "aaaa... " * 10
    result = chunker.process(text)
    assert len(result) > 1
    for chunk in result:
        assert len(chunk) <= 30


def test_validates_max_chars() -> None:
    """A non-positive max_chars should be rejected."""
    import pytest

    with pytest.raises(ValueError):
        SentenceChunker(max_chars=0)