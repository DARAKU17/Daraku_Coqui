"""Tests for pause injection."""

from __future__ import annotations

from chronovoice.processing.pauses import PauseInjector, PauseRule


RULES: list[tuple[str, int]] = [
    (r"Here's the twist\.", 350),
    (r"Imagine\.\.\.", 500),
]


def test_injects_break_tag() -> None:
    """A matched phrase should have a break tag appended."""
    injector = PauseInjector(rules=RULES)
    result = injector.process("Here's the twist. Next.")
    assert result == "Here's the twist.<break=350ms> Next."


def test_multiple_rules_apply() -> None:
    """Each matching rule should inject its break."""
    injector = PauseInjector(rules=RULES)
    result = injector.process("Imagine... Hello Here's the twist.")
    assert "<break=500ms>" in result
    assert "<break=350ms>" in result


def test_case_insensitive_matching() -> None:
    """Rules should match regardless of case."""
    injector = PauseInjector(rules=RULES)
    result = injector.process("HERE'S THE TWIST.")
    assert result == "HERE'S THE TWIST.<break=350ms>"


def test_no_match_no_change() -> None:
    """Text without a matching phrase must pass through unchanged."""
    injector = PauseInjector(rules=RULES)
    assert injector.process("Nothing special here.") == "Nothing special here."


def test_uses_provided_pause_ms() -> None:
    """A rule should use its own pause length."""
    rule = PauseRule(pattern=r"Wait\.", pause_ms=400)
    injector = PauseInjector(rules=[rule])
    assert injector.process("Wait. go") == "Wait.<break=400ms> go"


def test_add_rule_at_runtime() -> None:
    """Rules can be registered after construction."""
    injector = PauseInjector(rules=[])
    injector.add_rule(r"Congratulations\.", pause_ms=600)
    result = injector.process("Congratulations. done")
    assert result == "Congratulations.<break=600ms> done"