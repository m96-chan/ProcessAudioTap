#!/usr/bin/env python3
"""
macOS PyObjC audio capture test (Phase 2).

This script tests the full PyObjC-based Core Audio implementation including
actual audio capture from a process.

Phase 2 Testing:
- Process tap creation
- Audio I/O callback
- Audio data streaming
- Format configuration
- Error handling

Usage:
    python examples/macos_pyobjc_capture_test.py --pid 12345 --duration 5
    python examples/macos_pyobjc_capture_test.py --name Music --output test.wav

Requirements:
- macOS 14.4+
- PyObjC: pip install pyobjc-core pyobjc-framework-CoreAudio
- psutil (optional, for process listing): pip install psutil

Example:
    # Capture 5 seconds of audio from Music.app
    python examples/macos_pyobjc_capture_test.py --name Music --duration 5 --output music.wav

    # Capture from specific PID
    python examples/macos_pyobjc_capture_test.py --pid 12345 --duration 10 --output audio.wav
"""

from __future__ import annotations

import argparse
import sys
import time
import wave
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from proctap.backends import macos_pyobjc
except ImportError as e:
    print(f"ERROR: Failed to import macos_pyobjc module: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def find_pid_by_name(process_name: str) -> list[tuple[int, str]]:
    """
    Find PIDs by process name.

    Args:
        process_name: Process name to search for (case-insensitive)

    Returns:
        List of tuples (pid, full_name)

    Raises:
        RuntimeError: If psutil is not available
    """
    try:
        import psutil
    except ImportError:
        raise RuntimeError(
            "psutil is required for process name lookup. "
            "Install it with: pip install psutil"
        )

    matching_processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                matching_processes.append((proc.info['pid'], proc.info['name']))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return matching_processes


def save_audio_to_wav(
    audio_chunks: list[bytes],
    output_path: str,
    sample_rate: int = 48000,
    channels: int = 2,
    sample_width: int = 2
) -> None:
    """
    Save captured audio chunks to WAV file.

    Args:
        audio_chunks: List of PCM audio data chunks
        output_path: Output WAV file path
        sample_rate: Sample rate in Hz
        channels: Number of channels
        sample_width: Bytes per sample
    """
    if not audio_chunks:
        print("WARNING: No audio data captured")
        return

    with wave.open(output_path, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)

        for chunk in audio_chunks:
            wav_file.writeframes(chunk)

    # Calculate total duration
    total_bytes = sum(len(chunk) for chunk in audio_chunks)
    total_frames = total_bytes // (channels * sample_width)
    duration = total_frames / sample_rate

    print(f"Saved {len(audio_chunks)} chunks to {output_path}")
    print(f"Total size: {total_bytes:,} bytes")
    print(f"Duration: {duration:.2f} seconds")


def test_audio_capture(
    pid: int,
    duration: float = 5.0,
    output_path: str | None = None,
    sample_rate: int = 48000,
    channels: int = 2,
    sample_width: int = 2
) -> int:
    """
    Test audio capture from a process.

    Args:
        pid: Process ID to capture from
        duration: Capture duration in seconds
        output_path: Optional output WAV file path
        sample_rate: Sample rate in Hz
        channels: Number of channels
        sample_width: Bytes per sample

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print(f"Testing PyObjC audio capture for PID {pid}")
    print(f"Configuration: {sample_rate}Hz, {channels}ch, {sample_width * 8}bit")
    print(f"Duration: {duration} seconds")
    print("=" * 60)

    try:
        # Create backend
        print("Creating MacOSNativeBackend...")
        backend = macos_pyobjc.MacOSNativeBackend(
            pid=pid,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width
        )

        # Start capture
        print("Starting audio capture...")
        backend.start()

        # Capture audio
        print(f"Capturing audio for {duration} seconds...")
        audio_chunks = []
        start_time = time.time()
        chunk_count = 0

        while time.time() - start_time < duration:
            chunk = backend.read()
            if chunk:
                audio_chunks.append(chunk)
                chunk_count += 1

                # Progress indicator
                elapsed = time.time() - start_time
                if chunk_count % 10 == 0:
                    print(f"  [{elapsed:.1f}s] Captured {chunk_count} chunks, "
                          f"{sum(len(c) for c in audio_chunks):,} bytes", end='\r')

            time.sleep(0.01)  # Small sleep to prevent busy loop

        print()  # New line after progress

        # Stop capture
        print("Stopping audio capture...")
        backend.stop()

        # Results
        print("=" * 60)
        print("Capture Results:")
        print(f"  Total chunks: {len(audio_chunks)}")
        total_bytes = sum(len(chunk) for chunk in audio_chunks)
        print(f"  Total bytes: {total_bytes:,}")

        if total_bytes > 0:
            actual_duration = total_bytes / (sample_rate * channels * sample_width)
            print(f"  Actual duration: {actual_duration:.2f} seconds")
            print()
            print("Phase 2 Test: PASSED ✓")

            # Save to file if requested
            if output_path:
                print()
                save_audio_to_wav(
                    audio_chunks,
                    output_path,
                    sample_rate,
                    channels,
                    sample_width
                )

            return 0
        else:
            print()
            print("Phase 2 Test: FAILED (no audio data captured)")
            print()
            print("Possible reasons:")
            print("  - Process is not currently playing audio")
            print("  - Audio capture permission not granted")
            print("  - Process terminated during capture")
            return 1

    except Exception as e:
        print(f"✗ Error during capture: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("Phase 2 Test: FAILED (exception)")
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test PyObjC Core Audio audio capture (Phase 2)"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--pid',
        type=int,
        help='Process ID to capture from'
    )
    group.add_argument(
        '--name',
        type=str,
        help='Process name to search for (e.g., "Music", "Safari")'
    )

    parser.add_argument(
        '--duration',
        type=float,
        default=5.0,
        help='Capture duration in seconds (default: 5.0)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output WAV file path (optional)'
    )
    parser.add_argument(
        '--sample-rate',
        type=int,
        default=48000,
        help='Sample rate in Hz (default: 48000)'
    )
    parser.add_argument(
        '--channels',
        type=int,
        default=2,
        choices=[1, 2],
        help='Number of channels (default: 2)'
    )
    parser.add_argument(
        '--bits',
        type=int,
        default=16,
        choices=[8, 16, 24, 32],
        help='Bits per sample (default: 16)'
    )

    args = parser.parse_args()

    # Check PyObjC availability
    if not macos_pyobjc.is_available():
        print("ERROR: PyObjC Core Audio not available")
        print()
        print("Install with:")
        print("  pip install pyobjc-core pyobjc-framework-CoreAudio")
        return 1

    # Check macOS version
    if not macos_pyobjc.supports_process_tap():
        major, minor, patch = macos_pyobjc.get_macos_version()
        print(f"ERROR: macOS {major}.{minor}.{patch} does not support Process Tap API")
        print("Requires macOS 14.4 (Sonoma) or later")
        return 1

    major, minor, patch = macos_pyobjc.get_macos_version()
    print(f"macOS Version: {major}.{minor}.{patch}")
    print(f"PyObjC Status: Available ✓")
    print(f"Process Tap API: Supported ✓")
    print()

    # Resolve PID
    if args.name:
        print(f"Searching for process: {args.name}")
        try:
            matching_processes = find_pid_by_name(args.name)

            if not matching_processes:
                print(f"✗ No process found with name containing '{args.name}'")
                return 1

            if len(matching_processes) > 1:
                print(f"Found {len(matching_processes)} matching processes:")
                for pid, name in matching_processes:
                    print(f"  PID {pid:6d}: {name}")
                print()
                print(f"Using first match: PID {matching_processes[0][0]}")

            pid, process_name = matching_processes[0]
            print(f"Target: {process_name} (PID {pid})")
            print()

        except Exception as e:
            print(f"✗ Error: {e}")
            return 1
    else:
        pid = args.pid

    # Run capture test
    sample_width = args.bits // 8
    return test_audio_capture(
        pid=pid,
        duration=args.duration,
        output_path=args.output,
        sample_rate=args.sample_rate,
        channels=args.channels,
        sample_width=sample_width
    )


if __name__ == '__main__':
    sys.exit(main())
