"""
Contrib modules for ProcessAudioTap.

This package contains optional integrations and utilities that extend
ProcessAudioTap's functionality.
"""

from __future__ import annotations

__all__: list[str] = []

try:
    from .discord_source import ProcessAudioSource
    __all__.append("ProcessAudioSource")
except ImportError:
    # discord.py is not installed
    pass
