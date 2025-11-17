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


def get_backend(
    pid: int,
    sample_rate: int = 44100,
    channels: int = 2,
    sample_width: int = 2,
) -> "AudioBackend":
    """
    Get the appropriate audio capture backend for the current platform.

    Args:
        pid: Process ID to capture audio from
        sample_rate: Sample rate in Hz (default: 44100)
        channels: Number of channels (default: 2 for stereo)
        sample_width: Bytes per sample (default: 2 for 16-bit)

    Returns:
        Platform-specific AudioBackend implementation

    Raises:
        NotImplementedError: If the current platform is not supported
        ImportError: If the backend for the current platform cannot be loaded

    Note:
        Windows backend now supports format conversion. The native WASAPI
        captures at 44100Hz/2ch/16-bit, but will convert to the specified format.
    """
    system = platform.system()

    if system == "Windows":
        from .windows import WindowsBackend
        return WindowsBackend(
            pid=pid,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
        )

    elif system == "Linux":
        from .linux import LinuxBackend
        return LinuxBackend(
            pid=pid,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
        )

    elif system == "Darwin":  # macOS
        # Official macOS backend: PyObjC (Phase 3)
        # Other backends (Swift CLI, C extension) are experimental only

        try:
            from .macos_pyobjc import MacOSNativeBackend, is_available
            if is_available():
                import logging
                logging.getLogger(__name__).info(
                    "Using PyObjC backend (Official macOS backend - Phase 3)"
                )
                return MacOSNativeBackend(
                    pid=pid,
                    sample_rate=sample_rate,
                    channels=channels,
                    sample_width=sample_width,
                )
            else:
                raise RuntimeError(
                    "Core Audio framework not available. "
                    "macOS 14.4+ (Sonoma) is required for Process Tap API."
                )
        except ImportError as e:
            raise RuntimeError(
                "macOS backend requires PyObjC. Install with:\n"
                "  pip install pyobjc-core pyobjc-framework-CoreAudio\n"
                f"Error: {e}"
            ) from e

    else:
        raise NotImplementedError(
            f"Platform '{system}' is not supported. "
            "Supported platforms: Windows, Linux (in development), macOS (planned)"
        )


__all__ = ["get_backend", "AudioBackend"]
