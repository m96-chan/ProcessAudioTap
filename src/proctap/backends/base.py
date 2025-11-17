"""
Abstract base class for platform-specific audio capture backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class AudioBackend(ABC):
    """
    Abstract base class for audio capture backends.

    Each platform-specific backend must implement these methods to provide
    process-specific audio capture functionality.
    """

    def __init__(self, pid: int) -> None:
        """
        Initialize the backend for a specific process.

        Args:
            pid: Process ID to capture audio from
        """
        self._pid = pid

    @property
    def pid(self) -> int:
        """Get the target process ID."""
        return self._pid

    @abstractmethod
    def start(self) -> None:
        """
        Start audio capture from the target process.

        Raises:
            RuntimeError: If capture fails to start
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop audio capture.

        Should be safe to call multiple times.
        """
        pass

    @abstractmethod
    def read(self) -> Optional[bytes]:
        """
        Read audio data from the capture buffer.

        Returns:
            PCM audio data as bytes, or None if no data is available

        Note:
            This method should not block for extended periods.
            Return None quickly if no data is available.
        """
        pass

    @abstractmethod
    def get_format(self) -> dict[str, int | object]:
        """
        Get audio format information.

        Returns:
            Dictionary with keys:
            - 'sample_rate': Sample rate in Hz (e.g., 44100)
            - 'channels': Number of channels (e.g., 2 for stereo)
            - 'bits_per_sample': Bits per sample (e.g., 16)
            - Additional backend-specific keys may be present
        """
        pass
