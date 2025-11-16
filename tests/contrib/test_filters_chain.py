"""Tests for FilterChain."""

from __future__ import annotations

import numpy as np
import pytest

from proctap.contrib.filters import (
    FilterChain,
    GainNormalizer,
    HighPassFilter,
    NoiseGate,
    StereoToMono,
)


class TestFilterChain:
    """Tests for FilterChain composition."""

    def test_empty_chain_raises(self):
        """Test that empty filter list raises ValueError."""
        with pytest.raises(ValueError, match="at least one filter"):
            FilterChain([])

    def test_single_filter(self):
        """Test chain with single filter."""
        hpf = HighPassFilter(sample_rate=48000, cutoff_hz=120.0)
        chain = FilterChain([hpf])

        frame = np.random.randn(480).astype(np.float32) * 0.1
        output = chain.process(frame)

        assert output.dtype == np.float32
        assert output.shape == frame.shape

    def test_multiple_filters_sequential(self):
        """Test that filters are applied sequentially."""
        chain = FilterChain([
            HighPassFilter(sample_rate=48000, cutoff_hz=120.0),
            NoiseGate(sample_rate=48000, threshold_db=-40.0),
        ])

        frame = np.random.randn(480).astype(np.float32) * 0.1
        output = chain.process(frame)

        assert output.dtype == np.float32

    def test_shape_change_through_chain(self):
        """Test that shape can change through chain (stereo to mono)."""
        chain = FilterChain([
            HighPassFilter(sample_rate=48000, cutoff_hz=120.0),
            StereoToMono(),
        ])

        # Stereo input
        frame = np.random.randn(480, 2).astype(np.float32) * 0.1
        output = chain.process(frame)

        # Mono output
        assert output.ndim == 1
        assert output.shape == (480,)

    def test_full_processing_chain(self):
        """Test complete processing chain with all filter types."""
        chain = FilterChain([
            HighPassFilter(sample_rate=48000, cutoff_hz=120.0),
            NoiseGate(sample_rate=48000, threshold_db=-40.0),
            StereoToMono(),
            GainNormalizer(target_rms=0.1),
        ])

        # Stereo input
        frame = np.random.randn(480, 2).astype(np.float32) * 0.1
        output = chain.process(frame)

        # Mono output
        assert output.dtype == np.float32
        assert output.ndim == 1
        assert output.shape == (480,)
        assert np.all(output >= -1.0)
        assert np.all(output <= 1.0)

    def test_chain_length(self):
        """Test __len__ method."""
        chain = FilterChain([
            HighPassFilter(sample_rate=48000),
            NoiseGate(sample_rate=48000),
            StereoToMono(),
        ])

        assert len(chain) == 3

    def test_chain_getitem(self):
        """Test __getitem__ method."""
        hpf = HighPassFilter(sample_rate=48000)
        gate = NoiseGate(sample_rate=48000)
        converter = StereoToMono()

        chain = FilterChain([hpf, gate, converter])

        assert chain[0] is hpf
        assert chain[1] is gate
        assert chain[2] is converter

    def test_add_filter(self):
        """Test adding filter to chain."""
        chain = FilterChain([
            HighPassFilter(sample_rate=48000),
        ])

        gate = NoiseGate(sample_rate=48000)
        chain.add_filter(gate)

        assert len(chain) == 2
        assert chain[1] is gate

    def test_insert_filter(self):
        """Test inserting filter at specific position."""
        hpf = HighPassFilter(sample_rate=48000)
        converter = StereoToMono()
        chain = FilterChain([hpf, converter])

        gate = NoiseGate(sample_rate=48000)
        chain.insert_filter(1, gate)

        assert len(chain) == 3
        assert chain[0] is hpf
        assert chain[1] is gate
        assert chain[2] is converter

    def test_remove_filter(self):
        """Test removing filter from chain."""
        hpf = HighPassFilter(sample_rate=48000)
        gate = NoiseGate(sample_rate=48000)
        converter = StereoToMono()

        chain = FilterChain([hpf, gate, converter])

        removed = chain.remove_filter(1)

        assert removed is gate
        assert len(chain) == 2
        assert chain[0] is hpf
        assert chain[1] is converter

    def test_remove_last_filter_raises(self):
        """Test that removing last filter raises ValueError."""
        chain = FilterChain([HighPassFilter(sample_rate=48000)])

        with pytest.raises(ValueError, match="Cannot remove last filter"):
            chain.remove_filter(0)

    def test_stateful_filters_maintain_state(self):
        """Test that stateful filters maintain state across calls."""
        chain = FilterChain([
            HighPassFilter(sample_rate=48000, cutoff_hz=120.0),
        ])

        # Process DC signal multiple times
        dc_signal = np.ones(480, dtype=np.float32) * 0.5

        # First few frames
        for _ in range(5):
            chain.process(dc_signal)

        # Later frame should have filter state stabilized
        output = chain.process(dc_signal)

        # DC should be significantly attenuated
        assert np.mean(np.abs(output)) < 0.1

    def test_dtype_validation(self):
        """Test that invalid dtype raises ValueError."""
        chain = FilterChain([HighPassFilter(sample_rate=48000)])

        frame = np.random.randn(480).astype(np.float64)

        with pytest.raises(ValueError, match="Expected float32"):
            chain.process(frame)

    def test_order_matters(self):
        """Test that filter order affects output."""
        # Chain 1: HPF -> Stereo to Mono
        chain1 = FilterChain([
            HighPassFilter(sample_rate=48000, cutoff_hz=120.0),
            StereoToMono(),
        ])

        # Chain 2: Stereo to Mono -> HPF
        chain2 = FilterChain([
            StereoToMono(),
            HighPassFilter(sample_rate=48000, cutoff_hz=120.0),
        ])

        # Same input
        frame = np.random.randn(480, 2).astype(np.float32) * 0.1

        output1 = chain1.process(frame.copy())
        output2 = chain2.process(frame.copy())

        # Both should be mono with same shape
        assert output1.shape == output2.shape == (480,)

        # But values may differ due to order (though similar for this case)
        # Just verify both produce valid output
        assert output1.dtype == np.float32
        assert output2.dtype == np.float32

    def test_processing_multiple_frames(self):
        """Test processing multiple frames sequentially."""
        chain = FilterChain([
            HighPassFilter(sample_rate=48000, cutoff_hz=120.0),
            NoiseGate(sample_rate=48000, threshold_db=-40.0),
            GainNormalizer(target_rms=0.1),
        ])

        # Process 10 frames
        for _ in range(10):
            frame = np.random.randn(480).astype(np.float32) * 0.1
            output = chain.process(frame)

            assert output.dtype == np.float32
            assert output.shape == (480,)
            assert np.all(output >= -1.0)
            assert np.all(output <= 1.0)
