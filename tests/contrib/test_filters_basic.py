"""Basic tests for individual audio filters."""

from __future__ import annotations

import numpy as np
import pytest

from proctap.contrib.filters import (
    EnergyVAD,
    GainNormalizer,
    HighPassFilter,
    LowPassFilter,
    NoiseGate,
    StereoToMono,
)


class TestHighPassFilter:
    """Tests for HighPassFilter."""

    def test_dtype_preserved(self):
        """Test that output dtype is float32."""
        hpf = HighPassFilter(sample_rate=48000, cutoff_hz=120.0)
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = hpf.process(frame)

        assert output.dtype == np.float32

    def test_shape_preserved_mono(self):
        """Test that mono shape is preserved."""
        hpf = HighPassFilter(sample_rate=48000, cutoff_hz=120.0)
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = hpf.process(frame)

        assert output.shape == frame.shape

    def test_shape_preserved_stereo(self):
        """Test that stereo shape is preserved."""
        hpf = HighPassFilter(sample_rate=48000, cutoff_hz=120.0)
        frame = np.random.randn(480, 2).astype(np.float32) * 0.1

        output = hpf.process(frame)

        assert output.shape == frame.shape

    def test_removes_dc_offset(self):
        """Test that DC offset is attenuated."""
        hpf = HighPassFilter(sample_rate=48000, cutoff_hz=120.0)

        # Create signal with DC offset
        frame = np.ones(4800, dtype=np.float32) * 0.5

        # Process multiple frames to let filter stabilize
        for _ in range(10):
            output = hpf.process(frame)

        # DC should be significantly attenuated
        assert np.mean(np.abs(output)) < 0.1

    def test_invalid_dtype_raises(self):
        """Test that invalid dtype raises ValueError."""
        hpf = HighPassFilter(sample_rate=48000, cutoff_hz=120.0)
        frame = np.random.randn(480).astype(np.float64)

        with pytest.raises(ValueError, match="Expected float32"):
            hpf.process(frame)


class TestLowPassFilter:
    """Tests for LowPassFilter."""

    def test_dtype_preserved(self):
        """Test that output dtype is float32."""
        lpf = LowPassFilter(sample_rate=48000, cutoff_hz=8000.0)
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = lpf.process(frame)

        assert output.dtype == np.float32

    def test_shape_preserved_mono(self):
        """Test that mono shape is preserved."""
        lpf = LowPassFilter(sample_rate=48000, cutoff_hz=8000.0)
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = lpf.process(frame)

        assert output.shape == frame.shape

    def test_shape_preserved_stereo(self):
        """Test that stereo shape is preserved."""
        lpf = LowPassFilter(sample_rate=48000, cutoff_hz=8000.0)
        frame = np.random.randn(480, 2).astype(np.float32) * 0.1

        output = lpf.process(frame)

        assert output.shape == frame.shape

    def test_smooths_signal(self):
        """Test that high-frequency noise is attenuated."""
        lpf = LowPassFilter(sample_rate=48000, cutoff_hz=1000.0)

        # Create high-frequency noise
        t = np.arange(480) / 48000.0
        high_freq = np.sin(2 * np.pi * 10000.0 * t).astype(np.float32)

        # Process
        output = lpf.process(high_freq)

        # Output should have lower energy than input
        assert np.std(output) < np.std(high_freq)


class TestStereoToMono:
    """Tests for StereoToMono."""

    def test_dtype_preserved(self):
        """Test that output dtype is float32."""
        converter = StereoToMono()
        frame = np.random.randn(480, 2).astype(np.float32) * 0.1

        output = converter.process(frame)

        assert output.dtype == np.float32

    def test_stereo_to_mono_conversion(self):
        """Test that stereo is converted to mono."""
        converter = StereoToMono()
        frame = np.random.randn(480, 2).astype(np.float32) * 0.1

        output = converter.process(frame)

        assert output.ndim == 1
        assert output.shape == (480,)

    def test_mono_unchanged(self):
        """Test that mono input is unchanged."""
        converter = StereoToMono()
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = converter.process(frame)

        assert output.ndim == 1
        assert output.shape == frame.shape
        np.testing.assert_array_equal(output, frame)

    def test_averaging(self):
        """Test that channels are averaged correctly."""
        converter = StereoToMono()

        # Create known stereo signal
        left = np.ones(480, dtype=np.float32) * 0.5
        right = np.ones(480, dtype=np.float32) * -0.5
        frame = np.column_stack([left, right])

        output = converter.process(frame)

        # Average should be zero
        np.testing.assert_allclose(output, 0.0, atol=1e-6)


class TestNoiseGate:
    """Tests for NoiseGate."""

    def test_dtype_preserved(self):
        """Test that output dtype is float32."""
        gate = NoiseGate(sample_rate=48000, threshold_db=-40.0)
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = gate.process(frame)

        assert output.dtype == np.float32

    def test_shape_preserved(self):
        """Test that shape is preserved."""
        gate = NoiseGate(sample_rate=48000, threshold_db=-40.0)
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = gate.process(frame)

        assert output.shape == frame.shape

    def test_attenuates_quiet_signal(self):
        """Test that quiet signals are attenuated."""
        gate = NoiseGate(sample_rate=48000, threshold_db=-40.0)

        # Very quiet signal (below threshold)
        frame = np.random.randn(4800).astype(np.float32) * 0.0001

        # Process multiple frames
        for _ in range(10):
            output = gate.process(frame)

        # Output should be significantly quieter
        assert np.mean(np.abs(output)) < np.mean(np.abs(frame)) * 0.5

    def test_passes_loud_signal(self):
        """Test that loud signals pass through."""
        gate = NoiseGate(sample_rate=48000, threshold_db=-40.0)

        # Loud signal (above threshold)
        frame = np.random.randn(480).astype(np.float32) * 0.5

        output = gate.process(frame)

        # Output should be similar to input
        assert np.mean(np.abs(output)) > 0.3


class TestGainNormalizer:
    """Tests for GainNormalizer."""

    def test_dtype_preserved(self):
        """Test that output dtype is float32."""
        normalizer = GainNormalizer(target_rms=0.1)
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = normalizer.process(frame)

        assert output.dtype == np.float32

    def test_shape_preserved(self):
        """Test that shape is preserved."""
        normalizer = GainNormalizer(target_rms=0.1)
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = normalizer.process(frame)

        assert output.shape == frame.shape

    def test_clipping_prevention(self):
        """Test that output is clipped to valid range."""
        normalizer = GainNormalizer(target_rms=0.5, max_gain_db=30.0)
        frame = np.random.randn(480).astype(np.float32) * 2.0  # Potentially out of range

        output = normalizer.process(frame)

        # Output should be within [-1.0, 1.0]
        assert np.all(output >= -1.0)
        assert np.all(output <= 1.0)

    def test_normalizes_level(self):
        """Test that quiet signal is amplified."""
        normalizer = GainNormalizer(target_rms=0.1, adaptation_rate=0.1)

        # Very quiet signal
        frame = np.random.randn(480).astype(np.float32) * 0.01

        # Process multiple frames to let normalizer adapt
        for _ in range(50):
            output = normalizer.process(frame)

        # Output should be louder than input
        assert np.mean(np.abs(output)) > np.mean(np.abs(frame))


class TestEnergyVAD:
    """Tests for EnergyVAD."""

    def test_dtype_preserved(self):
        """Test that output dtype is float32."""
        vad = EnergyVAD(threshold_db=-45.0)
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = vad.process(frame)

        assert output.dtype == np.float32

    def test_shape_preserved(self):
        """Test that shape is preserved."""
        vad = EnergyVAD(threshold_db=-45.0)
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = vad.process(frame)

        assert output.shape == frame.shape

    def test_audio_unchanged(self):
        """Test that audio passes through unchanged."""
        vad = EnergyVAD(threshold_db=-45.0)
        frame = np.random.randn(480).astype(np.float32) * 0.1

        output = vad.process(frame)

        np.testing.assert_array_equal(output, frame)

    def test_detects_loud_signal(self):
        """Test that loud signal is detected as speech."""
        vad = EnergyVAD(threshold_db=-45.0)

        # Loud signal
        frame = np.random.randn(480).astype(np.float32) * 0.5

        vad.process(frame)

        assert vad.is_speech is True

    def test_detects_quiet_as_silence(self):
        """Test that quiet signal is detected as silence."""
        vad = EnergyVAD(threshold_db=-45.0, hangover_frames=0)

        # Very quiet signal
        frame = np.random.randn(480).astype(np.float32) * 0.0001

        vad.process(frame)

        assert vad.is_speech is False

    def test_hangover_mechanism(self):
        """Test that hangover keeps speech flag active."""
        vad = EnergyVAD(threshold_db=-45.0, hangover_frames=3)

        # First, loud signal
        loud_frame = np.random.randn(480).astype(np.float32) * 0.5
        vad.process(loud_frame)
        assert vad.is_speech is True

        # Then quiet signal - should still be speech due to hangover
        quiet_frame = np.random.randn(480).astype(np.float32) * 0.0001

        vad.process(quiet_frame)
        assert vad.is_speech is True  # Frame 1 of hangover

        vad.process(quiet_frame)
        assert vad.is_speech is True  # Frame 2 of hangover

        vad.process(quiet_frame)
        assert vad.is_speech is True  # Frame 3 of hangover

        vad.process(quiet_frame)
        assert vad.is_speech is False  # Hangover expired

    def test_detect_method(self):
        """Test that detect() method works independently."""
        vad = EnergyVAD(threshold_db=-45.0)

        loud_frame = np.random.randn(480).astype(np.float32) * 0.5
        result = vad.detect(loud_frame)

        assert result is True
        assert vad.is_speech is True
