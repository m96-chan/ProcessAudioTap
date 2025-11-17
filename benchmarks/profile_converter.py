"""
Advanced profiling for audio format converter (Issue #9 Phase 2).

This script provides detailed profiling information including:
- Function-level CPU profiling with cProfile
- Memory usage profiling with tracemalloc
- Line-by-line profiling for hot paths
- Platform-specific performance analysis
- Bottleneck identification

Usage:
    python benchmarks/profile_converter.py [--scenario SCENARIO] [--output-dir DIR]

Scenarios:
    all              - Run all profiling scenarios (default)
    simple           - Simple format conversions (no resampling)
    resampling       - Conversions with resampling
    channel          - Channel conversion scenarios
    bitdepth         - Bit depth conversion scenarios
    realtime         - Real-time streaming simulation
"""

import argparse
import cProfile
import pstats
import io
import time
import tracemalloc
import platform
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Callable
import numpy as np

from proctap.backends.converter import AudioConverter, SampleFormat


class ProfileResult:
    """Container for profiling results."""

    def __init__(self, name: str):
        self.name = name
        self.cpu_stats: pstats.Stats | None = None
        self.memory_peak: int = 0  # bytes
        self.memory_current: int = 0  # bytes
        self.execution_time: float = 0.0  # seconds
        self.iterations: int = 0
        self.avg_time_ms: float = 0.0

    def __str__(self) -> str:
        return (
            f"ProfileResult({self.name}):\n"
            f"  Execution time: {self.execution_time:.4f}s\n"
            f"  Iterations: {self.iterations}\n"
            f"  Avg per iteration: {self.avg_time_ms:.4f}ms\n"
            f"  Peak memory: {self.memory_peak / 1024 / 1024:.2f} MB\n"
            f"  Current memory: {self.memory_current / 1024 / 1024:.2f} MB"
        )


class ConverterProfiler:
    """Profiler for AudioConverter with CPU and memory analysis."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[ProfileResult] = []

    def profile_scenario(
        self,
        name: str,
        converter: AudioConverter,
        pcm_data: bytes,
        iterations: int = 1000,
    ) -> ProfileResult:
        """
        Profile a conversion scenario with CPU and memory profiling.

        Args:
            name: Scenario name
            converter: AudioConverter instance
            pcm_data: Input PCM data
            iterations: Number of iterations to run

        Returns:
            ProfileResult with profiling data
        """
        result = ProfileResult(name)
        result.iterations = iterations

        # Start memory tracking
        tracemalloc.start()

        # Create profiler
        profiler = cProfile.Profile()

        # Warmup
        for _ in range(10):
            converter.convert(pcm_data)

        # Clear memory baseline
        tracemalloc.clear_traces()

        # Profile execution
        start_time = time.perf_counter()
        profiler.enable()

        for _ in range(iterations):
            converter.convert(pcm_data)

        profiler.disable()
        end_time = time.perf_counter()

        # Collect memory stats
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Store results
        result.execution_time = end_time - start_time
        result.avg_time_ms = (result.execution_time / iterations) * 1000
        result.memory_current = current
        result.memory_peak = peak

        # Store CPU stats
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.strip_dirs()
        ps.sort_stats(pstats.SortKey.CUMULATIVE)
        result.cpu_stats = ps

        self.results.append(result)
        return result

    def generate_report(self, result: ProfileResult, top_n: int = 20) -> str:
        """Generate detailed profiling report."""
        report = []
        report.append("=" * 80)
        report.append(f"Profile Report: {result.name}")
        report.append("=" * 80)
        report.append("")
        report.append(f"Platform: {platform.system()} {platform.release()}")
        report.append(f"Python: {sys.version.split()[0]}")
        report.append(f"NumPy: {np.__version__}")
        report.append("")
        report.append("Performance Metrics:")
        report.append(f"  Total execution time: {result.execution_time:.4f} seconds")
        report.append(f"  Iterations: {result.iterations}")
        report.append(f"  Average time per iteration: {result.avg_time_ms:.4f} ms")
        report.append(f"  Throughput: {result.iterations / result.execution_time:.2f} conversions/sec")
        report.append("")
        report.append("Memory Metrics:")
        report.append(f"  Peak memory usage: {result.memory_peak / 1024 / 1024:.2f} MB")
        report.append(f"  Current memory usage: {result.memory_current / 1024 / 1024:.2f} MB")
        report.append(f"  Memory per iteration: {result.memory_peak / result.iterations / 1024:.2f} KB")
        report.append("")
        report.append(f"Top {top_n} Functions by Cumulative Time:")
        report.append("-" * 80)

        # Capture CPU stats
        s = io.StringIO()
        if result.cpu_stats:
            result.cpu_stats.print_stats(top_n)
            report.append(s.getvalue())

        return "\n".join(report)

    def save_report(self, result: ProfileResult, filename: str | None = None):
        """Save profiling report to file."""
        if filename is None:
            filename = f"profile_{result.name.replace(' ', '_').lower()}.txt"

        report = self.generate_report(result)
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            f.write(report)

        print(f"Report saved to: {filepath}")

    def save_callgrind(self, result: ProfileResult, filename: str | None = None):
        """Save profiling data in callgrind format for visualization."""
        if filename is None:
            filename = f"profile_{result.name.replace(' ', '_').lower()}.prof"

        filepath = self.output_dir / filename

        if result.cpu_stats:
            result.cpu_stats.dump_stats(str(filepath))
            print(f"Callgrind data saved to: {filepath}")
            print(f"  View with: snakeviz {filepath}")


# Profiling scenarios

def create_simple_conversion_scenarios() -> List[Tuple[str, Callable[[], Tuple[AudioConverter, bytes]]]]:
    """Create simple conversion scenarios (no resampling)."""
    scenarios = []

    def stereo_16bit_to_16bit():
        converter = AudioConverter(
            src_rate=44100, src_channels=2, src_width=2,
            dst_rate=44100, dst_channels=2, dst_width=2,
            auto_detect_format=False
        )
        num_samples = int(44100 * 0.01)
        audio = (np.sin(2 * np.pi * 440 * np.arange(num_samples) / 44100) * 32767).astype(np.int16)
        stereo = np.tile(audio, (2, 1)).T.flatten()
        return converter, stereo.tobytes()

    scenarios.append(("Simple: Stereo 16-bit (no conversion)", stereo_16bit_to_16bit))

    def stereo_to_mono():
        converter = AudioConverter(
            src_rate=44100, src_channels=2, src_width=2,
            dst_rate=44100, dst_channels=1, dst_width=2,
            auto_detect_format=False
        )
        num_samples = int(44100 * 0.01)
        audio = (np.sin(2 * np.pi * 440 * np.arange(num_samples) / 44100) * 32767).astype(np.int16)
        stereo = np.tile(audio, (2, 1)).T.flatten()
        return converter, stereo.tobytes()

    scenarios.append(("Simple: Stereo to Mono", stereo_to_mono))

    def mono_to_stereo():
        converter = AudioConverter(
            src_rate=44100, src_channels=1, src_width=2,
            dst_rate=44100, dst_channels=2, dst_width=2,
            auto_detect_format=False
        )
        num_samples = int(44100 * 0.01)
        audio = (np.sin(2 * np.pi * 440 * np.arange(num_samples) / 44100) * 32767).astype(np.int16)
        return converter, audio.tobytes()

    scenarios.append(("Simple: Mono to Stereo", mono_to_stereo))

    return scenarios


def create_bitdepth_conversion_scenarios() -> List[Tuple[str, Callable[[], Tuple[AudioConverter, bytes]]]]:
    """Create bit depth conversion scenarios."""
    scenarios = []

    def bit16_to_bit24():
        converter = AudioConverter(
            src_rate=44100, src_channels=2, src_width=2,
            dst_rate=44100, dst_channels=2, dst_width=3,
            src_format=SampleFormat.INT16,
            dst_format=SampleFormat.INT24,
            auto_detect_format=False
        )
        num_samples = int(44100 * 0.01) * 2
        audio = (np.sin(2 * np.pi * 440 * np.arange(num_samples) / 44100) * 32767).astype(np.int16)
        return converter, audio.tobytes()

    scenarios.append(("BitDepth: 16-bit to 24-bit", bit16_to_bit24))

    def bit24_to_bit16():
        converter = AudioConverter(
            src_rate=44100, src_channels=2, src_width=3,
            dst_rate=44100, dst_channels=2, dst_width=2,
            src_format=SampleFormat.INT24,
            dst_format=SampleFormat.INT16,
            auto_detect_format=False
        )
        num_samples = int(44100 * 0.01) * 2
        audio_int = (np.sin(2 * np.pi * 440 * np.arange(num_samples) / 44100) * 8388607).astype(np.int32)
        pcm_bytes = bytearray()
        for val in audio_int:
            pcm_bytes.extend([val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF])
        return converter, bytes(pcm_bytes)

    scenarios.append(("BitDepth: 24-bit to 16-bit", bit24_to_bit16))

    return scenarios


def create_resampling_scenarios() -> List[Tuple[str, Callable[[], Tuple[AudioConverter, bytes]]]]:
    """Create resampling scenarios."""
    scenarios = []

    def resample_44_to_48():
        converter = AudioConverter(
            src_rate=44100, src_channels=2, src_width=2,
            dst_rate=48000, dst_channels=2, dst_width=2,
            auto_detect_format=False
        )
        num_samples = int(44100 * 0.01)
        audio = (np.sin(2 * np.pi * 440 * np.arange(num_samples) / 44100) * 32767).astype(np.int16)
        stereo = np.tile(audio, (2, 1)).T.flatten()
        return converter, stereo.tobytes()

    scenarios.append(("Resample: 44.1kHz to 48kHz", resample_44_to_48))

    def resample_48_to_44():
        converter = AudioConverter(
            src_rate=48000, src_channels=2, src_width=2,
            dst_rate=44100, dst_channels=2, dst_width=2,
            auto_detect_format=False
        )
        num_samples = int(48000 * 0.01)
        audio = (np.sin(2 * np.pi * 440 * np.arange(num_samples) / 48000) * 32767).astype(np.int16)
        stereo = np.tile(audio, (2, 1)).T.flatten()
        return converter, stereo.tobytes()

    scenarios.append(("Resample: 48kHz to 44.1kHz", resample_48_to_44))

    def resample_and_channel():
        converter = AudioConverter(
            src_rate=44100, src_channels=2, src_width=2,
            dst_rate=48000, dst_channels=1, dst_width=2,
            auto_detect_format=False
        )
        num_samples = int(44100 * 0.01)
        audio = (np.sin(2 * np.pi * 440 * np.arange(num_samples) / 44100) * 32767).astype(np.int16)
        stereo = np.tile(audio, (2, 1)).T.flatten()
        return converter, stereo.tobytes()

    scenarios.append(("Complex: Resample + Channel Conversion", resample_and_channel))

    return scenarios


def create_channel_conversion_scenarios() -> List[Tuple[str, Callable[[], Tuple[AudioConverter, bytes]]]]:
    """Create channel conversion scenarios."""
    scenarios = []

    def stereo_to_5_1():
        converter = AudioConverter(
            src_rate=44100, src_channels=2, src_width=2,
            dst_rate=44100, dst_channels=6, dst_width=2,
            auto_detect_format=False
        )
        num_samples = int(44100 * 0.01)
        audio = (np.sin(2 * np.pi * 440 * np.arange(num_samples) / 44100) * 32767).astype(np.int16)
        stereo = np.tile(audio, (2, 1)).T.flatten()
        return converter, stereo.tobytes()

    scenarios.append(("Channel: Stereo to 5.1", stereo_to_5_1))

    def surround_5_1_to_stereo():
        converter = AudioConverter(
            src_rate=44100, src_channels=6, src_width=2,
            dst_rate=44100, dst_channels=2, dst_width=2,
            auto_detect_format=False
        )
        num_samples = int(44100 * 0.01)
        audio = (np.sin(2 * np.pi * 440 * np.arange(num_samples) / 44100) * 32767).astype(np.int16)
        surround = np.tile(audio, (6, 1)).T.flatten()
        return converter, surround.tobytes()

    scenarios.append(("Channel: 5.1 to Stereo", surround_5_1_to_stereo))

    return scenarios


def run_profiling(scenarios: List[Tuple[str, Callable]], profiler: ConverterProfiler, iterations: int = 1000):
    """Run profiling for a list of scenarios."""
    for name, scenario_fn in scenarios:
        print(f"\nProfiling: {name}")
        print("-" * 80)

        converter, pcm_data = scenario_fn()

        result = profiler.profile_scenario(name, converter, pcm_data, iterations)

        print(result)
        print(f"  Target: <1.0 ms per iteration")
        print(f"  Status: {'✅ PASS' if result.avg_time_ms < 1.0 else '❌ FAIL (resample expected)'}")

        # Save reports
        profiler.save_report(result)
        profiler.save_callgrind(result)


def main():
    parser = argparse.ArgumentParser(
        description="Profile audio format converter performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--scenario',
        choices=['all', 'simple', 'resampling', 'channel', 'bitdepth'],
        default='all',
        help='Profiling scenario to run'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('profiling_results'),
        help='Output directory for profiling reports'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=1000,
        help='Number of iterations per scenario'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Audio Format Converter Profiling")
    print("Issue #9 Phase 2: Profiling")
    print("=" * 80)
    print(f"\nPlatform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print(f"NumPy: {np.__version__}")
    print(f"Output directory: {args.output_dir}")
    print(f"Iterations per scenario: {args.iterations}")
    print("")

    profiler = ConverterProfiler(args.output_dir)

    # Select scenarios
    all_scenarios = []
    if args.scenario in ['all', 'simple']:
        all_scenarios.extend(create_simple_conversion_scenarios())
    if args.scenario in ['all', 'bitdepth']:
        all_scenarios.extend(create_bitdepth_conversion_scenarios())
    if args.scenario in ['all', 'channel']:
        all_scenarios.extend(create_channel_conversion_scenarios())
    if args.scenario in ['all', 'resampling']:
        all_scenarios.extend(create_resampling_scenarios())

    # Run profiling
    run_profiling(all_scenarios, profiler, args.iterations)

    # Generate summary
    print("\n" + "=" * 80)
    print("PROFILING SUMMARY")
    print("=" * 80)

    for result in profiler.results:
        status = '✅ PASS' if result.avg_time_ms < 1.0 else '⚠️  HIGH' if result.avg_time_ms < 2.0 else '❌ FAIL'
        print(f"\n{result.name}:")
        print(f"  Avg time: {result.avg_time_ms:.4f} ms - {status}")
        print(f"  Peak memory: {result.memory_peak / 1024 / 1024:.2f} MB")

    print("\n" + "=" * 80)
    print(f"All profiling reports saved to: {args.output_dir}")
    print("=" * 80)


if __name__ == '__main__':
    main()
