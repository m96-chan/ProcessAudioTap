"""
macOS audio capture backend (NOT YET IMPLEMENTED).

This module is a placeholder for future macOS support.
Process-specific audio capture on macOS requires integration with Core Audio
and potentially private APIs or system extensions.

STATUS: Not implemented - research needed
"""

from __future__ import annotations

from typing import Optional
import logging
import warnings

from .base import AudioBackend

logger = logging.getLogger(__name__)


class MacOSBackend(AudioBackend):
    """
    macOS implementation for process-specific audio capture.

    ❌ NOT IMPLEMENTED: This backend is a placeholder only.

    Potential approaches (research needed):
    - Core Audio framework with process filtering
    - Audio Unit loopback with application targeting
    - System Extensions (macOS 10.15+) for audio routing
    - Third-party drivers (e.g., BlackHole, Loopback)

    Current status: Placeholder - implementation approach not yet determined
    """

    def __init__(self, pid: int) -> None:
        """
        Initialize macOS backend (placeholder).

        Args:
            pid: Process ID to capture audio from

        Raises:
            NotImplementedError: Always - this backend is not implemented
        """
        super().__init__(pid)

        raise NotImplementedError(
            "macOS audio capture is not yet implemented. "
            "This platform is planned for future support. "
            "\n\n"
            "Potential implementation approaches:\n"
            "1. Core Audio framework with application-specific routing\n"
            "2. Audio Server plugins for process isolation\n"
            "3. System Extensions (requires code signing and user approval)\n"
            "\n"
            "Contributions welcome! See src/proctap/backends/macos.py"
        )

    def start(self) -> None:
        """Not implemented."""
        raise NotImplementedError("macOS backend is not implemented")

    def stop(self) -> None:
        """Not implemented."""
        raise NotImplementedError("macOS backend is not implemented")

    def read(self) -> Optional[bytes]:
        """Not implemented."""
        raise NotImplementedError("macOS backend is not implemented")

    def get_format(self) -> dict[str, int]:
        """Not implemented."""
        raise NotImplementedError("macOS backend is not implemented")


# Research notes for future implementers:
#
# macOS Audio Architecture:
# ------------------------
# macOS uses Core Audio as its primary audio framework, but process-specific
# capture is not straightforward.
#
# Challenges:
# 1. No built-in process loopback like Windows WASAPI
# 2. System audio routing is protected (SIP - System Integrity Protection)
# 3. Modern macOS versions have strict privacy controls
#
# Potential Approaches:
#
# Approach 1: Audio Unit + Application Filtering
# -----------------------------------------------
# - Use Audio Unit framework to create custom audio processing
# - Requires application cooperation or system-level hooks
# - May need audio driver or system extension
#
# Approach 2: System Extension (AudioServerPlugin)
# -------------------------------------------------
# - Create a System Extension that hooks into CoreAudio server
# - Requires code signing with Developer ID
# - User must approve in Security & Privacy settings
# - Most powerful but complex to deploy
#
# Approach 3: Virtual Audio Device + Application Routing
# -------------------------------------------------------
# - Use virtual audio device (like BlackHole)
# - Programmatically route target application to virtual device
# - Capture from virtual device
# - Requires user to configure audio output per-application
#
# Approach 4: Screen Recording API (macOS 10.15+)
# ------------------------------------------------
# - ScreenCaptureKit can capture application audio
# - Requires screen recording permission
# - Designed for screen capture but includes audio
# - Might be the most "official" way for per-app capture
#
# References:
# - Core Audio: https://developer.apple.com/documentation/coreaudio
# - Audio Units: https://developer.apple.com/documentation/audiounit
# - System Extensions: https://developer.apple.com/documentation/systemextensions
# - ScreenCaptureKit: https://developer.apple.com/documentation/screencapturekit
# - BlackHole (open source reference): https://github.com/ExistentialAudio/BlackHole
#
# Most Promising Path (as of 2025):
# - Use ScreenCaptureKit for macOS 12.3+
# - Falls back to requiring virtual audio device for older versions
# - This provides the most "legitimate" per-application audio capture
#
# TODO: Investigate ScreenCaptureKit feasibility
# TODO: Create prototype using SCContentSharingPicker
# TODO: Test privacy permission handling
