"""
Windows audio capture backend using WASAPI Process Loopback.

This backend wraps the native C++ extension (_native) for Windows-specific
process audio capture functionality.
"""

from __future__ import annotations

from typing import Optional
import logging

from .base import AudioBackend

logger = logging.getLogger(__name__)


class WindowsBackend(AudioBackend):
    """
    Windows implementation using WASAPI Process Loopback.

    Requires:
    - Windows 10 20H1 or later
    - C++ native extension (_native)
    """

    def __init__(self, pid: int) -> None:
        """
        Initialize Windows backend.

        Args:
            pid: Process ID to capture audio from

        Raises:
            ImportError: If the native extension cannot be imported
        """
        super().__init__(pid)

        try:
            from .._native import ProcessLoopback  # type: ignore[attr-defined]
            self._native = ProcessLoopback(pid)
            logger.debug(f"Initialized Windows WASAPI backend for PID {pid}")
        except ImportError as e:
            raise ImportError(
                "Native extension (_native) could not be imported. "
                "Please build the extension with: pip install -e .\n"
                f"Original error: {e}"
            ) from e

    def start(self) -> None:
        """Start WASAPI audio capture."""
        self._native.start()
        logger.debug(f"Started audio capture for PID {self._pid}")

    def stop(self) -> None:
        """Stop WASAPI audio capture."""
        try:
            self._native.stop()
            logger.debug(f"Stopped audio capture for PID {self._pid}")
        except Exception as e:
            logger.error(f"Error stopping capture: {e}")

    def read(self) -> Optional[bytes]:
        """
        Read audio data from WASAPI capture buffer.

        Returns:
            PCM audio data as bytes, or empty bytes if no data available
        """
        return self._native.read()

    def get_format(self) -> dict[str, int]:
        """
        Get audio format from native backend.

        Returns:
            Dictionary with 'sample_rate', 'channels', 'bits_per_sample'

        Note:
            The Windows native backend uses a fixed format:
            - 44100 Hz sample rate
            - 2 channels (stereo)
            - 16 bits per sample
        """
        return self._native.get_format()
