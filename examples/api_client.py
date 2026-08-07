"""Example client for the ChronoVoice HTTP API.

Requires the server running: ``chronovoice api`` or ``uvicorn chronovoice.api.main:app``.

This example uses only the standard library so it can run anywhere.
"""

from __future__ import annotations

import sys
from urllib import request

BASE_URL: str = "http://127.0.0.1:8000"


def health() -> None:
    """Print the health endpoint payload."""
    with request.urlopen(f"{BASE_URL}/health") as response:
        print(response.read().decode())


def synth(text: str) -> None:
    """Synthesise narration and print the output path."""
    payload = f'{{"text": "{text}"}}'.encode()
    req = request.Request(
        f"{BASE_URL}/tts",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req) as response:
        print(response.read().decode())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        health()
    else:
        text = sys.argv[1] if len(sys.argv) > 1 else "Hello from my cloned voice."
        synth(text)