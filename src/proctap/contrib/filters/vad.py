"""Voice Activity Detection (VAD) filters."""

from __future__ import annotations

import numpy as np

from .base import BaseFilter


class EnergyVAD(BaseFilter):
    """
    Simple energy-based Voice Activity Detection.

    Detects speech/voice based on signal energy level with hangover
    mechanism to prevent choppy detection.

    Args:
        threshold_db: Energy threshold in dB. Default is -45.0 dB.
        hangover_frames: Number of frames to keep speech flag active
                        after energy drops below threshold. Default is 5.

    Example:
        ```python
        vad = EnergyVAD(threshold_db=-45.0, hangover_frames=5)
        output = vad.process(audio_frame)

        if vad.is_speech:
            print("Speech detected!")
        ```
    """

    def __init__(
        self,
        threshold_db: float = -45.0,
        hangover_frames: int = 5,
    ):
        """Initialize energy-based VAD."""
        self.threshold_db = threshold_db
        self.hangover_frames = hangover_frames

        # Convert threshold to linear scale
        self.threshold_linear = 10.0 ** (threshold_db / 20.0)

        # Speech detection state
        self._is_speech = False
        self._hangover_counter = 0

    @property
    def is_speech(self) -> bool:
        """
        Get current speech detection state.

        Returns:
            True if speech is detected, False otherwise.
        """
        return self._is_speech

    def detect(self, frame: np.ndarray) -> bool:
        """
        Detect speech in audio frame.

        This method is called automatically by process(), but can also
        be called independently for detection without modifying the audio.

        Args:
            frame: Input audio frame (float32).

        Returns:
            True if speech is detected, False otherwise.
        """
        if frame.dtype != np.float32:
            raise ValueError(f"Expected float32, got {frame.dtype}")

        # Calculate RMS energy
        if frame.ndim == 1:
            rms = np.sqrt(np.mean(frame**2))
        else:
            # Use maximum RMS across channels
            rms = np.sqrt(np.max(np.mean(frame**2, axis=0)))

        # Check if energy exceeds threshold
        if rms > self.threshold_linear:
            # Speech detected
            self._is_speech = True
            self._hangover_counter = self.hangover_frames
        else:
            # No speech, but check hangover
            if self._hangover_counter > 0:
                self._hangover_counter -= 1
                self._is_speech = True
            else:
                self._is_speech = False

        return self._is_speech

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Process audio frame and update speech detection state.

        The audio is passed through unchanged, but speech detection
        state is updated and can be queried via is_speech property.

        Args:
            frame: Input audio frame (float32).

        Returns:
            Unmodified audio frame (float32).
        """
        # Update detection state
        self.detect(frame)

        # Return audio unchanged
        return frame
