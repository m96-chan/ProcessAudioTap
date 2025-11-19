#!/usr/bin/env python3
"""
Test script for macOS Swift CLI Helper backend.

This script tests the Swift CLI helper implementation that uses
Core Audio Process Tap API for per-process audio capture.

Usage:
    python examples/macos_swift_helper_test.py --pid <PID> --duration 5
    python examples/macos_swift_helper_test.py --name "Chrome" --duration 5

Requirements:
    - macOS 14.4+ (Sonoma)
    - Swift helper binary built (cd swift/proctap-helper && swift build -c release)
    - Target process must be actively playing audio
    - Microphone permission (TCC prompt will appear)
"""

import argparse
import logging
import sys
import time
import wave
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import psutil
except ImportError:
    psutil = None

from proctap.backends.macos_swift_helper import SwiftHelperBackend, is_available


def find_process_by_name(name: str) -> int:
    """Find process ID by name (requires psutil)."""
    if psutil is None:
        raise RuntimeError("psutil not installed. Install with: pip install psutil")

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if name.lower() in proc.info['name'].lower():
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    raise ValueError(f"Process '{name}' not found")


def main():
    parser = argparse.ArgumentParser(
        description="Test macOS Swift CLI Helper backend for Process Tap API"
    )
    parser.add_argument(
        "--pid",
        type=int,
        help="Process ID to capture audio from",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Process name to search for (requires psutil)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="Recording duration in seconds (default: 5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("swift_helper_test.wav"),
        help="Output WAV file path (default: swift_helper_test.wav)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=48000,
        help="Sample rate in Hz (default: 48000)",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=2,
        choices=[1, 2],
        help="Number of channels (default: 2)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Get PID
    if args.pid:
        pid = args.pid
    elif args.name:
        try:
            pid = find_process_by_name(args.name)
            print(f"Found process '{args.name}' with PID {pid}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        parser.error("Either --pid or --name must be specified")
        return 1

    # Check availability
    if not is_available():
        print("Error: Swift CLI Helper backend not available", file=sys.stderr)
        print("\nBuild Swift helper with:", file=sys.stderr)
        print("  cd swift/proctap-helper && swift build -c release", file=sys.stderr)
        return 1

    print(f"\n=== Swift CLI Helper Test ===")
    print(f"PID: {pid}")
    print(f"Duration: {args.duration}s")
    print(f"Sample Rate: {args.sample_rate} Hz")
    print(f"Channels: {args.channels}")
    print(f"Output: {args.output}")
    print(f"{'='*30}\n")

    # Create backend
    try:
        backend = SwiftHelperBackend(
            pid=pid,
            sample_rate=args.sample_rate,
            channels=args.channels,
            sample_width=2,  # 16-bit
        )
    except Exception as e:
        print(f"Error creating backend: {e}", file=sys.stderr)
        return 1

    # Open WAV file
    wav_file = wave.open(str(args.output), 'wb')
    wav_file.setnchannels(args.channels)
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(args.sample_rate)

    # Statistics
    total_bytes = 0
    total_chunks = 0
    start_time = time.time()

    def on_audio_data(chunk: bytes, frame_count: int):
        """Callback for audio chunks."""
        nonlocal total_bytes, total_chunks
        wav_file.writeframes(chunk)
        total_bytes += len(chunk)
        total_chunks += 1

        # Progress indicator
        elapsed = time.time() - start_time
        print(f"\rCapturing... {elapsed:.1f}s | {total_bytes/1024:.1f} KB | {total_chunks} chunks", end='')

    # Start capture
    print("Starting capture...")
    print("(Make sure target process is playing audio)\n")

    try:
        backend.start(callback=on_audio_data)

        # Wait for duration
        time.sleep(args.duration)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    except Exception as e:
        print(f"\n\nError during capture: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Stop capture
        print("\n\nStopping capture...")
        backend.stop()
        wav_file.close()

    # Report statistics
    elapsed = time.time() - start_time
    print(f"\n=== Capture Complete ===")
    print(f"Duration: {elapsed:.2f}s")
    print(f"Total data: {total_bytes/1024:.1f} KB ({total_bytes} bytes)")
    print(f"Total chunks: {total_chunks}")
    print(f"Average rate: {total_bytes/elapsed/1024:.1f} KB/s")
    print(f"Output file: {args.output}")
    print(f"File size: {args.output.stat().st_size/1024:.1f} KB")

    if total_bytes == 0:
        print("\n⚠️  WARNING: No audio data captured!")
        print("   - Check if target process is actually playing audio")
        print("   - Check if microphone permission is granted")
        print("   - Check Swift helper stderr output above for errors")
        return 1

    print(f"\n✅ Success! Audio captured to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
