"""
Real-time audio filtering library for ProcTap.

This package provides a collection of audio filters for real-time processing
of PCM audio data. All filters work with float32 NumPy arrays in the range
[-1.0, 1.0].

Available filters:
    - DSP: HighPassFilter, LowPassFilter, StereoToMono
    - Dynamics: NoiseGate, GainNormalizer
    - VAD: EnergyVAD
    - Composition: FilterChain

Example:
    ```python
    from proctap.contrib.filters import (
        HighPassFilter,
        NoiseGate,
        StereoToMono,
        GainNormalizer,
        FilterChain,
    )

    # Create filter chain
    chain = FilterChain([
        HighPassFilter(sample_rate=48000, cutoff_hz=120.0),
        NoiseGate(sample_rate=48000, threshold_db=-40.0),
        StereoToMono(),
        GainNormalizer(target_rms=0.1),
    ])

    # Process audio
    processed = chain.process(audio_frame)
    ```
"""

from __future__ import annotations

from .base import BaseFilter
from .chain import FilterChain
from .dsp import HighPassFilter, LowPassFilter, StereoToMono
from .dynamics import GainNormalizer, NoiseGate
from .vad import EnergyVAD

__all__ = [
    "BaseFilter",
    "HighPassFilter",
    "LowPassFilter",
    "StereoToMono",
    "NoiseGate",
    "GainNormalizer",
    "EnergyVAD",
    "FilterChain",
]
