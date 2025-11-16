"""
Contrib modules for ProcessAudioCapture.

This package contains optional integrations and utilities that extend
ProcessAudioCapture's functionality.
"""

from __future__ import annotations

__all__: list[str] = []

try:
    from .discord_source import ProcessAudioSource
    __all__.append("ProcessAudioSource")
except ImportError:
    # discord.py is not installed
    pass

try:
    from .whisper_transcribe import RealtimeTranscriber
    __all__.append("RealtimeTranscriber")
except ImportError:
    # faster-whisper is not installed
    pass
