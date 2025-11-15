"""
Backend selection module for ProcTap.

Automatically selects the appropriate audio capture backend based on the
current operating system.
"""

from __future__ import annotations

import sys
import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import AudioBackend


def get_backend(pid: int) -> "AudioBackend":
    """
    Get the appropriate audio capture backend for the current platform.

    Args:
        pid: Process ID to capture audio from

    Returns:
        Platform-specific AudioBackend implementation

    Raises:
        NotImplementedError: If the current platform is not supported
        ImportError: If the backend for the current platform cannot be loaded
    """
    system = platform.system()

    if system == "Windows":
        from .windows import WindowsBackend
        return WindowsBackend(pid)

    elif system == "Linux":
        from .linux import LinuxBackend
        return LinuxBackend(pid)

    elif system == "Darwin":  # macOS
        from .macos import MacOSBackend
        return MacOSBackend(pid)

    else:
        raise NotImplementedError(
            f"Platform '{system}' is not supported. "
            "Supported platforms: Windows, Linux (in development), macOS (planned)"
        )


__all__ = ["get_backend", "AudioBackend"]
