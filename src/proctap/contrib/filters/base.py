"""Base filter abstract class for audio processing."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class BaseFilter(ABC):
    """
    Abstract base class for audio filters.

    All filters process PCM audio data as float32 NumPy arrays with values
    in the range [-1.0, 1.0].

    Input/Output format:
        - dtype: np.float32
        - shape: (N,) for mono, (N, C) for multi-channel
        - value range: -1.0 to 1.0

    Example:
        ```python
        class CustomFilter(BaseFilter):
            def process(self, frame: np.ndarray) -> np.ndarray:
                # Apply custom processing
                return frame * 0.5  # Simple gain reduction
        ```
    """

    @abstractmethod
    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Process an audio frame.

        Args:
            frame: Input audio frame as float32 array.
                   Shape: (N,) for mono or (N, C) for multi-channel.
                   Values should be in range [-1.0, 1.0].

        Returns:
            Processed audio frame with same dtype (float32).
            Output shape may differ depending on filter type
            (e.g., stereo-to-mono conversion).

        Raises:
            ValueError: If input frame has invalid dtype or shape.
        """
        pass
