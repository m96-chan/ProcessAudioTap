"""Dynamics processing filters (noise gate, gain normalization)."""

from __future__ import annotations

import numpy as np

from .base import BaseFilter


class NoiseGate(BaseFilter):
    """
    Simple noise gate with attack and release envelopes.

    Reduces gain when input level falls below threshold, attenuating
    background noise during silence.

    Args:
        sample_rate: Audio sample rate in Hz.
        threshold_db: Gate threshold in dB. Default is -40.0 dB.
        attack_ms: Attack time in milliseconds. Default is 5.0 ms.
        release_ms: Release time in milliseconds. Default is 50.0 ms.

    Example:
        ```python
        gate = NoiseGate(sample_rate=48000, threshold_db=-40.0)
        gated = gate.process(audio_frame)
        ```
    """

    def __init__(
        self,
        sample_rate: int,
        threshold_db: float = -40.0,
        attack_ms: float = 5.0,
        release_ms: float = 50.0,
    ):
        """Initialize noise gate."""
        self.sample_rate = sample_rate
        self.threshold_db = threshold_db
        self.attack_ms = attack_ms
        self.release_ms = release_ms

        # Convert threshold to linear scale
        self.threshold_linear = 10.0 ** (threshold_db / 20.0)

        # Calculate attack/release coefficients
        self.attack_coeff = np.exp(-1.0 / (sample_rate * attack_ms / 1000.0))
        self.release_coeff = np.exp(-1.0 / (sample_rate * release_ms / 1000.0))

        # Current gate gain (0.0 = fully closed, 1.0 = fully open)
        self.current_gain = 1.0

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply noise gate to audio frame.

        Args:
            frame: Input audio frame (float32).

        Returns:
            Gated audio frame (float32).
        """
        if frame.dtype != np.float32:
            raise ValueError(f"Expected float32, got {frame.dtype}")

        output = np.empty_like(frame)

        # Process sample by sample (or frame by frame for multi-channel)
        for i in range(len(frame)):
            # Get current sample(s)
            if frame.ndim == 1:
                sample = frame[i]
                level = abs(sample)
            else:
                sample = frame[i]
                # Use max level across channels
                level = np.max(np.abs(sample))

            # Determine target gain based on threshold
            if level > self.threshold_linear:
                target_gain = 1.0  # Gate open
            else:
                target_gain = 0.0  # Gate closed

            # Smooth gain change with attack/release
            if target_gain > self.current_gain:
                # Attack (opening gate)
                self.current_gain = (
                    self.attack_coeff * self.current_gain
                    + (1.0 - self.attack_coeff) * target_gain
                )
            else:
                # Release (closing gate)
                self.current_gain = (
                    self.release_coeff * self.current_gain
                    + (1.0 - self.release_coeff) * target_gain
                )

            # Apply gain
            output[i] = sample * self.current_gain

        return output.astype(np.float32)


class GainNormalizer(BaseFilter):
    """
    Automatic gain control to normalize audio to target RMS level.

    Adapts gain based on running RMS estimate to maintain consistent
    output level.

    Args:
        target_rms: Target RMS level (linear scale). Default is 0.1.
        max_gain_db: Maximum gain in dB. Default is 12.0 dB.
        adaptation_rate: Rate of gain adaptation (0.0-1.0). Default is 0.01.

    Example:
        ```python
        normalizer = GainNormalizer(target_rms=0.1, max_gain_db=12.0)
        normalized = normalizer.process(audio_frame)
        ```
    """

    def __init__(
        self,
        target_rms: float = 0.1,
        max_gain_db: float = 12.0,
        adaptation_rate: float = 0.01,
    ):
        """Initialize gain normalizer."""
        self.target_rms = target_rms
        self.max_gain_db = max_gain_db
        self.adaptation_rate = adaptation_rate

        # Convert max gain to linear scale
        self.max_gain_linear = 10.0 ** (max_gain_db / 20.0)

        # Running RMS estimate
        self.running_rms = target_rms

        # Current gain
        self.current_gain = 1.0

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply gain normalization to audio frame.

        Args:
            frame: Input audio frame (float32).

        Returns:
            Normalized audio frame (float32).
        """
        if frame.dtype != np.float32:
            raise ValueError(f"Expected float32, got {frame.dtype}")

        # Calculate RMS of current frame
        if frame.ndim == 1:
            frame_rms = np.sqrt(np.mean(frame**2))
        else:
            # Use maximum RMS across channels
            frame_rms = np.sqrt(np.max(np.mean(frame**2, axis=0)))

        # Update running RMS with exponential moving average
        if frame_rms > 1e-6:  # Avoid updating on silence
            self.running_rms = (
                1.0 - self.adaptation_rate
            ) * self.running_rms + self.adaptation_rate * frame_rms

        # Calculate required gain to reach target RMS
        if self.running_rms > 1e-6:
            required_gain = self.target_rms / self.running_rms
        else:
            required_gain = 1.0

        # Limit gain to maximum
        required_gain = min(required_gain, self.max_gain_linear)

        # Smooth gain change
        self.current_gain = (
            0.99 * self.current_gain + 0.01 * required_gain
        )

        # Apply gain
        output = frame * self.current_gain

        # Clip to prevent overflow
        output = np.clip(output, -1.0, 1.0)

        return output.astype(np.float32)
