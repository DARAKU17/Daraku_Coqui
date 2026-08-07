"""Inserting short pauses after rhetorical phrases.

Human narration breathes after phrases like "Here's the twist." and
"Imagine...". XTTS v2 understands a ``<break>`` tag, so the injector
rewrites rule matches to append a timed pause. Rules are a list of
``(pattern, pause_ms)`` tuples; adding a rule is as simple as appending a
tuple or loading a JSON file of rules.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

#: Tags used to express silence to XTTS v2.
_BREAK_TEMPLATE: str = "<break={pause}ms>"


@dataclass(frozen=True)
class PauseRule:
    """A single pause-injection rule.

    Attributes:
        pattern: Regex matched against the text.
        pause_ms: Silence inserted after the match, in milliseconds.
    """

    pattern: str
    pause_ms: int


class PauseInjector:
    """Appends timed pauses after phrases matching configured rules.

    Args:
        rules: Iterable of ``(pattern, pause_ms)`` tuples.
        default_pause_ms: Silence used when a rule carries no pause length.
    """

    def __init__(
        self,
        rules: list[PauseRule] | list[tuple[str, int]] | None = None,
        default_pause_ms: int = 350,
    ) -> None:
        """Initialise the injector with a rule set.

        Args:
            rules: Optional ``(pattern, pause_ms)`` pairs.
            default_pause_ms: Fallback pause length in milliseconds.
        """
        self._rules: list[PauseRule] = self._normalize_rules(rules)
        self._default_pause_ms: int = default_pause_ms

    @classmethod
    def from_json(cls, path: str | Path, default_pause_ms: int = 350) -> "PauseInjector":
        """Build an injector from a JSON rule file.

        The JSON file is a list of objects with ``pattern`` and ``pause_ms``
        keys, e.g.::

            [
                {"pattern": "Sounds impossible\\?", "pause_ms": 350},
                {"pattern": "Here's the twist\\.", "pause_ms": 350}
            ]

        Args:
            path: Path to the JSON rule file.
            default_pause_ms: Fallback pause length in milliseconds.

        Returns:
            A configured :class:`PauseInjector`.

        Raises:
            FileNotFoundError: If the rule file does not exist.
            ValueError: If the JSON structure is invalid.
        """
        rule_path = Path(path)
        if not rule_path.is_file():
            raise FileNotFoundError(f"Pause rules file not found: {rule_path}")
        with rule_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, list):
            raise ValueError("Pause rules JSON must be a list of objects")
        rules: list[tuple[str, int]] = []
        for entry in raw:
            if not isinstance(entry, dict) or "pattern" not in entry:
                raise ValueError("Each pause rule must be an object with 'pattern'")
            pause = int(entry.get("pause_ms", default_pause_ms))
            rules.append((str(entry["pattern"]), pause))
        return cls(rules=rules, default_pause_ms=default_pause_ms)

    def process(self, text: str) -> str:
        """Insert pauses into the text.

        Args:
            text: Cleaned text, typically a single chunk.

        Returns:
            The text with ``<break=Xms>`` tags inserted after rule matches.
        """
        for rule in self._rules:
            pattern = re.compile(rule.pattern, flags=re.IGNORECASE)
            pause = _BREAK_TEMPLATE.format(pause=rule.pause_ms)
            text = pattern.sub(rf"\g<0>{pause}", text)
        return text

    def add_rule(self, pattern: str, pause_ms: int | None = None) -> None:
        """Register a new rule at runtime.

        Args:
            pattern: Regex matched against the text.
            pause_ms: Pause length in milliseconds, falls back to default.
        """
        pause = pause_ms if pause_ms is not None else self._default_pause_ms
        self._rules.append(PauseRule(pattern=pattern, pause_ms=pause))

    @staticmethod
    def _normalize_rules(
        rules: list[PauseRule] | list[tuple[str, int]] | None,
    ) -> list[PauseRule]:
        """Coerce input rules into a uniform list of :class:`PauseRule`.

        Args:
            rules: Raw rules from the constructor.

        Returns:
            Normalized rule objects.
        """
        if not rules:
            return []
        normalized: list[PauseRule] = []
        for entry in rules:
            if isinstance(entry, PauseRule):
                normalized.append(entry)
            else:
                pattern, pause = entry
                normalized.append(PauseRule(pattern=pattern, pause_ms=pause))
        return normalized