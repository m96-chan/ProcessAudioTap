"""Filter chain for composing multiple filters."""

from __future__ import annotations

import numpy as np

from .base import BaseFilter


class FilterChain(BaseFilter):
    """
    Chain multiple filters to be applied sequentially.

    Allows composing multiple filters into a single processing pipeline.

    Args:
        filters: List of filters to apply in order.

    Example:
        ```python
        from proctap.contrib.filters import (
            HighPassFilter,
            NoiseGate,
            StereoToMono,
            GainNormalizer,
            FilterChain,
        )

        chain = FilterChain([
            HighPassFilter(sample_rate=48000, cutoff_hz=120.0),
            NoiseGate(sample_rate=48000, threshold_db=-40.0),
            StereoToMono(),
            GainNormalizer(target_rms=0.1),
        ])

        processed = chain.process(audio_frame)
        ```
    """

    def __init__(self, filters: list[BaseFilter]):
        """
        Initialize filter chain.

        Args:
            filters: List of filters to apply sequentially.

        Raises:
            ValueError: If filters list is empty.
        """
        if not filters:
            raise ValueError("Filter chain must contain at least one filter")

        self.filters = filters

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply all filters in the chain sequentially.

        Args:
            frame: Input audio frame (float32).

        Returns:
            Processed audio frame (float32) after applying all filters.
        """
        if frame.dtype != np.float32:
            raise ValueError(f"Expected float32, got {frame.dtype}")

        # Apply each filter in sequence
        output = frame
        for filter_instance in self.filters:
            output = filter_instance.process(output)

        return output

    def add_filter(self, filter_instance: BaseFilter) -> None:
        """
        Add a filter to the end of the chain.

        Args:
            filter_instance: Filter to add.
        """
        self.filters.append(filter_instance)

    def insert_filter(self, index: int, filter_instance: BaseFilter) -> None:
        """
        Insert a filter at a specific position in the chain.

        Args:
            index: Position to insert filter (0-based).
            filter_instance: Filter to insert.
        """
        self.filters.insert(index, filter_instance)

    def remove_filter(self, index: int) -> BaseFilter:
        """
        Remove and return a filter from the chain.

        Args:
            index: Index of filter to remove (0-based).

        Returns:
            Removed filter instance.

        Raises:
            ValueError: If removing the last filter (chain would be empty).
        """
        if len(self.filters) <= 1:
            raise ValueError("Cannot remove last filter from chain")

        return self.filters.pop(index)

    def __len__(self) -> int:
        """
        Get number of filters in the chain.

        Returns:
            Number of filters.
        """
        return len(self.filters)

    def __getitem__(self, index: int) -> BaseFilter:
        """
        Get filter at specified index.

        Args:
            index: Filter index (0-based).

        Returns:
            Filter instance at index.
        """
        return self.filters[index]
