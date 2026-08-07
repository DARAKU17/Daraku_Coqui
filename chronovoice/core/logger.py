"""Structured logging for ChronoVoice.

All logging goes through :func:`get_logger` so a single module logger
can be configured consistently. Logs are emitted as JSON documents when
the output is a stream, which keeps them greppable and machine-parseable.
Application code should ``get_logger(__name__)`` and never call ``print``
directly.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the record as a JSON object string.

        Args:
            record: The log record to serialize.

        Returns:
            A single line JSON string describing the record.
        """
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Include user supplied structured context if present.
        extra = getattr(record, "context", None)
        if isinstance(extra, dict):
            payload["context"] = extra
        return json.dumps(payload, default=str)


def _configure_root() -> None:
    """Configure the root logger once with JSON formatting."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Return a configured structured logger.

    Guarantees the root logger is configured before returning a child
    logger so formatting is consistent across the application.

    Args:
        name: The logger name, conventionally ``__name__``.

    Returns:
        A :class:`logging.Logger` that emits JSON records.
    """
    _configure_root()
    return logging.getLogger(name)