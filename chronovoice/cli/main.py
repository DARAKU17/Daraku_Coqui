"""Typer command-line interface for ChronoVoice.

The CLI mirrors the API surface and delegates all heavy lifting to the
service layer; it only renders results and reads user input.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from chronovoice.core.config import load_settings
from chronovoice.service.tts_service import get_default_service

app = typer.Typer(
    name="chronovoice",
    help="Local AI narration toolkit built on Coqui XTTS v2.",
    no_args_is_help=True,
)
voices_app = typer.Typer(
    name="voices",
    help="Manage the voice library.",
    no_args_is_help=True,
)
app.add_typer(voices_app, name="voices")

_console = Console()


@voices_app.command("list")
def voices_list() -> None:
    """List all registered voices in the library."""
    service = get_default_service()
    voices = service.voices_list()
    if not voices:
        _console.print("[yellow]No voices registered.[/yellow]")
        return
    table = Table(title="Voices")
    table.add_column("Name")
    table.add_column("Language")
    table.add_column("Sample Rate")
    table.add_column("Description")
    for voice in voices:
        table.add_row(
            voice.voice_name,
            voice.language,
            str(voice.sample_rate),
            voice.description,
        )
    _console.print(table)


@voices_app.command("add")
def voices_add(
    name: str = typer.Argument(..., help="Name for the new voice."),
    reference: Path = typer.Argument(..., help="Path to the reference audio (mp3/wav/ogg)."),
    language: str = typer.Option("en", "--language", "-l", help="Language code."),
    description: str = typer.Option("", "--description", "-d", help="Voice description."),
    sample_rate: int = typer.Option(22050, "--sample-rate", help="Sample rate in Hz."),
) -> None:
    """Register a new voice from a reference clip."""
    voice = get_default_service().voice_create(
        voice_name=name,
        reference_audio=reference,
        language=language,
        description=description,
        sample_rate=sample_rate,
    )
    _console.print(f"[green]Registered voice '{voice.voice_name}'.[/green]")


@app.command("synth")
def synth(
    text: str = typer.Argument(..., help="Narration text to synthesise."),
    voice: str | None = typer.Option(None, "--voice", help="Voice name to use."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output wav path."),
) -> None:
    """Generate a narration audio file from text."""
    result = get_default_service().synthesize(
        text=text,
        voice_name=voice,
        output_path=output,
    )
    _console.print(
        f"[green]Generated {result.output_path} [/green]"
        f"({result.chunk_count} chunk(s))."
    )


@app.command("health")
def health() -> None:
    """Show backend health and capability information."""
    payload = get_default_service().health()
    _console.print(
        f"Backend: {payload['backend']} (loaded: {payload['loaded']})\n"
        f"Multilingual: {payload['supports_multilingual']} | "
        f"Streaming: {payload['supports_streaming']} | "
        f"Voice cloning: {payload['supports_voice_cloning']}"
    )


@app.command("config")
def config() -> None:
    """Show the effective configuration."""
    settings = load_settings()
    _console.print(f"Backend: {settings.backend.name}")
    _console.print(f"Device: {settings.backend.device}")
    _console.print(f"Language: {settings.language}")
    _console.print(f"Voice: {settings.voice}")
    _console.print(f"Output dir: {settings.resolved_output_dir()}")
    _console.print(f"Chunk size: {settings.pipeline.chunk_size}")
    _console.print(f"Pause length: {settings.pipeline.pause_length} ms")
    _console.print(f"Sample rate: {settings.sample_rate}")


if __name__ == "__main__":
    app()