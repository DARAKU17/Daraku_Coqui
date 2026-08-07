"""FastAPI application factory for ChronoVoice."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from chronovoice.api import routes
from chronovoice.core.config import load_settings
from chronovoice.core.logger import get_logger
from chronovoice.service.tts_service import get_default_service

logger = get_logger(__name__)

__version__: str = "0.1.0"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage application startup and shutdown.

    The backend model is intentionally NOT loaded eagerly: XTTS is heavy and
    lazily loaded on first synthesis request. This lifespan only logs the
    active configuration and releases resources on shutdown.

    Yields:
        Nothing; used for setup/teardown side effects.
    """
    settings = load_settings()
    logger.info(
        "Starting ChronoVoice",
        extra={
            "context": {
                "backend": settings.backend.name,
                "device": settings.backend.device,
                "voice": settings.voice,
            }
        },
    )
    yield
    get_default_service().backends.unload()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Returns:
        A configured :class:`FastAPI` instance.
    """
    application = FastAPI(
        title="ChronoVoice",
        description="Local AI narration toolkit built on Coqui XTTS v2.",
        version=__version__,
        lifespan=lifespan,
    )
    application.include_router(routes.router)
    return application


app = create_app()