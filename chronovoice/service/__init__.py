"""Service layer orchestrating backends and processing pipelines."""

from chronovoice.service.tts_service import SynthesisResult, TTSService, TTSBackendManager

__all__ = ["TTSService", "TTSBackendManager", "SynthesisResult"]