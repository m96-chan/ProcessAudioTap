"""DSP filters for audio processing."""

from __future__ import annotations

import numpy as np

from .base import BaseFilter


class HighPassFilter(BaseFilter):
    """
    Simple first-order IIR high-pass filter.

    Removes low-frequency components below the cutoff frequency.
    Useful for removing DC offset and rumble.

    Args:
        sample_rate: Audio sample rate in Hz.
        cutoff_hz: Cutoff frequency in Hz. Default is 120.0 Hz.

    Example:
        ```python
        hpf = HighPassFilter(sample_rate=48000, cutoff_hz=120.0)
        filtered = hpf.process(audio_frame)
        ```
    """

    def __init__(self, sample_rate: int, cutoff_hz: float = 120.0):
        """Initialize high-pass filter."""
        self.sample_rate = sample_rate
        self.cutoff_hz = cutoff_hz

        # Calculate filter coefficient (first-order IIR)
        rc = 1.0 / (2.0 * np.pi * cutoff_hz)
        dt = 1.0 / sample_rate
        self.alpha = rc / (rc + dt)

        # State variable for each channel
        self.prev_input: np.ndarray | None = None
        self.prev_output: np.ndarray | None = None

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply high-pass filter to audio frame.

        Args:
            frame: Input audio frame (float32).

        Returns:
            Filtered audio frame (float32).
        """
        if frame.dtype != np.float32:
            raise ValueError(f"Expected float32, got {frame.dtype}")

        # Initialize state on first call
        if self.prev_input is None:
            if frame.ndim == 1:
                self.prev_input = np.zeros(1, dtype=np.float32)
                self.prev_output = np.zeros(1, dtype=np.float32)
            else:
                self.prev_input = np.zeros(frame.shape[1], dtype=np.float32)
                self.prev_output = np.zeros(frame.shape[1], dtype=np.float32)

        # Apply first-order IIR high-pass filter
        # y[n] = alpha * (y[n-1] + x[n] - x[n-1])
        assert self.prev_input is not None and self.prev_output is not None

        if frame.ndim == 1:
            # Mono
            output = np.empty_like(frame)
            output[0] = self.alpha * (self.prev_output[0] + frame[0] - self.prev_input[0])

            for i in range(1, len(frame)):
                output[i] = self.alpha * (output[i - 1] + frame[i] - frame[i - 1])

            self.prev_input[0] = frame[-1]
            self.prev_output[0] = output[-1]
        else:
            # Multi-channel
            output = np.empty_like(frame)
            output[0] = self.alpha * (self.prev_output + frame[0] - self.prev_input)

            for i in range(1, len(frame)):
                output[i] = self.alpha * (output[i - 1] + frame[i] - frame[i - 1])

            self.prev_input = frame[-1].copy()
            self.prev_output = output[-1].copy()

        return output.astype(np.float32)


class LowPassFilter(BaseFilter):
    """
    Simple first-order IIR low-pass filter.

    Removes high-frequency components above the cutoff frequency.
    Useful for anti-aliasing and smoothing.

    Args:
        sample_rate: Audio sample rate in Hz.
        cutoff_hz: Cutoff frequency in Hz. Default is 8000.0 Hz.

    Example:
        ```python
        lpf = LowPassFilter(sample_rate=48000, cutoff_hz=8000.0)
        filtered = lpf.process(audio_frame)
        ```
    """

    def __init__(self, sample_rate: int, cutoff_hz: float = 8000.0):
        """Initialize low-pass filter."""
        self.sample_rate = sample_rate
        self.cutoff_hz = cutoff_hz

        # Calculate filter coefficient (first-order IIR)
        rc = 1.0 / (2.0 * np.pi * cutoff_hz)
        dt = 1.0 / sample_rate
        self.alpha = dt / (rc + dt)

        # State variable
        self.prev_output: np.ndarray | None = None

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply low-pass filter to audio frame.

        Args:
            frame: Input audio frame (float32).

        Returns:
            Filtered audio frame (float32).
        """
        if frame.dtype != np.float32:
            raise ValueError(f"Expected float32, got {frame.dtype}")

        # Initialize state on first call
        if self.prev_output is None:
            if frame.ndim == 1:
                self.prev_output = np.zeros(1, dtype=np.float32)
            else:
                self.prev_output = np.zeros(frame.shape[1], dtype=np.float32)

        # Apply first-order IIR low-pass filter
        # y[n] = alpha * x[n] + (1 - alpha) * y[n-1]
        if frame.ndim == 1:
            # Mono
            output = np.empty_like(frame)
            output[0] = self.alpha * frame[0] + (1 - self.alpha) * self.prev_output[0]

            for i in range(1, len(frame)):
                output[i] = self.alpha * frame[i] + (1 - self.alpha) * output[i - 1]

            self.prev_output[0] = output[-1]
        else:
            # Multi-channel
            output = np.empty_like(frame)
            output[0] = self.alpha * frame[0] + (1 - self.alpha) * self.prev_output

            for i in range(1, len(frame)):
                output[i] = self.alpha * frame[i] + (1 - self.alpha) * output[i - 1]

            self.prev_output = output[-1].copy()

        return output.astype(np.float32)


class StereoToMono(BaseFilter):
    """
    Convert stereo (or multi-channel) audio to mono by averaging channels.

    If input is already mono, returns it unchanged.

    Example:
        ```python
        converter = StereoToMono()
        mono = converter.process(stereo_frame)  # (N, 2) -> (N,)
        ```
    """

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Convert multi-channel audio to mono.

        Args:
            frame: Input audio frame (float32).
                   Shape: (N,) or (N, C).

        Returns:
            Mono audio frame (float32).
            Shape: (N,).
        """
        if frame.dtype != np.float32:
            raise ValueError(f"Expected float32, got {frame.dtype}")

        if frame.ndim == 1:
            # Already mono
            return frame

        if frame.ndim == 2:
            # Average across channels
            result = np.mean(frame, axis=1, dtype=np.float32)
            # Ensure result is an ndarray (not a scalar)
            return np.asarray(result, dtype=np.float32)

        raise ValueError(f"Expected 1D or 2D array, got shape {frame.shape}")
