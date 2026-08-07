"""Data models for the voice library."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


def _utc_now() -> datetime:
    """Return the current UTC timestamp.

    Returns:
        Timezone-aware current datetime.
    """
    return datetime.now(timezone.utc)


class VoiceMetadata(BaseModel):
    """Metadata describing a registered voice.

    Attributes:
        voice_name: Unique name of the voice.
        language: Language code of the reference audio.
        description: Human readable description.
        created_at: ISO timestamp of when the voice was registered.
        sample_rate: Sample rate of the reference audio in Hz.
    """

    voice_name: str = Field(min_length=1)
    language: str = Field(default="en", min_length=2)
    description: str = Field(default="")
    created_at: datetime = Field(default_factory=_utc_now)
    sample_rate: int = Field(default=22050, ge=8000)

    @field_validator("voice_name")
    @classmethod
    def _validate_voice_name(cls, value: str) -> str:
        """Normalize and validate the voice name.

        Args:
            value: The raw voice name.

        Returns:
            A lowercased, whitespace-free voice name.

        Raises:
            ValueError: If the name contains unsafe characters.
        """
        cleaned = value.strip().lower().replace(" ", "_")
        if not cleaned or any(not (c.isalnum() or c in "_-") for c in cleaned):
            raise ValueError(
                "voice_name may only contain letters, numbers, underscores and hyphens"
            )
        return cleaned