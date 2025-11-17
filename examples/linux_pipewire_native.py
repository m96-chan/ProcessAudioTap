#!/usr/bin/env python3
"""
Linux PipeWire Native API capture example.

This example demonstrates ultra-low latency audio capture using the native
PipeWire C API bindings via ctypes.

Requirements:
- Linux with PipeWire 0.3+
- libpipewire-0.3.so (PipeWire development package)
- proctap with native PipeWire support: pip install proc-tap

Latency:
- Native API: ~2-5ms (vs ~10-20ms with subprocess-based approaches)
- Direct C API access eliminates subprocess overhead

Usage:
    python linux_pipewire_native.py --pid 12345 --duration 5 --output output.wav
    python linux_pipewire_native.py --name firefox --duration 10 --output firefox.wav

Note:
    - The target process must be actively playing audio
    - PipeWire daemon must be running
    - This example uses the native PipeWire API for maximum performance
"""

from __future__ import annotations

import argparse
import sys
import wave
import time
from pathlib import Path

try:
    from proctap.backends.linux import LinuxBackend
    from proctap.backends import pipewire_native
except ImportError:
    print("Error: proctap is not installed. Install it with: pip install proc-tap")
    sys.exit(1)


def find_pid_by_name(process_name: str) -> int:
    """
    Find PID by process name.

    Args:
        process_name: Process name to search for

    Returns:
        Process ID

    Raises:
        RuntimeError: If process not found or psutil not available
    """
    try:
        import psutil
    except ImportError:
        raise RuntimeError(
            "psutil is required to find process by name. "
            "Install it with: pip install psutil"
        )

    # Find processes with matching name
    matching_pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                matching_pids.append((proc.info['pid'], proc.info['name']))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if not matching_pids:
        raise RuntimeError(f"No process found with name containing '{process_name}'")

    if len(matching_pids) > 1:
        print(f"Found {len(matching_pids)} matching processes:")
        for pid, name in matching_pids:
            print(f"  PID {pid}: {name}")
        print(f"\nUsing first match: PID {matching_pids[0][0]}")

    return matching_pids[0][0]


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Capture audio from a specific process using PipeWire Native API"
    )

    # Process selection (mutually exclusive)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--pid',
        type=int,
        help='Process ID to capture audio from'
    )
    group.add_argument(
        '--name',
        type=str,
        help='Process name to search for (requires psutil)'
    )

    # Output options
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='output.wav',
        help='Output WAV file path (default: output.wav)'
    )
    parser.add_argument(
        '--duration', '-d',
        type=float,
        default=5.0,
        help='Recording duration in seconds (default: 5.0)'
    )

    # Audio format options
    parser.add_argument(
        '--sample-rate', '-r',
        type=int,
        default=48000,
        help='Sample rate in Hz (default: 48000 - PipeWire native)'
    )
    parser.add_argument(
        '--channels', '-c',
        type=int,
        default=2,
        choices=[1, 2],
        help='Number of channels: 1 (mono) or 2 (stereo) (default: 2)'
    )

    args = parser.parse_args()

    # Check if native PipeWire bindings are available
    if not pipewire_native.is_available():
        print("Error: PipeWire native bindings are not available!", file=sys.stderr)
        print("\nPossible reasons:", file=sys.stderr)
        print("  - libpipewire-0.3.so not found", file=sys.stderr)
        print("  - PipeWire development package not installed", file=sys.stderr)
        print("\nInstall PipeWire development package:", file=sys.stderr)
        print("  Ubuntu/Debian: sudo apt-get install libpipewire-0.3-dev", file=sys.stderr)
        print("  Fedora/RHEL:   sudo dnf install pipewire-devel", file=sys.stderr)
        print("  Arch:          sudo pacman -S pipewire", file=sys.stderr)
        return 1

    # Determine PID
    try:
        if args.name:
            print(f"Searching for process: {args.name}")
            pid = find_pid_by_name(args.name)
            print(f"Found PID: {pid}")
        else:
            pid = args.pid
            print(f"Using PID: {pid}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Prepare WAV file
    wav_file = wave.open(str(output_path), 'wb')
    wav_file.setnchannels(args.channels)
    wav_file.setsampwidth(2)  # 16-bit PCM
    wav_file.setframerate(args.sample_rate)

    frame_count = 0

    def on_audio_data(pcm_data: bytes, frames: int) -> None:
        """Callback function to write audio data to WAV file."""
        nonlocal frame_count
        wav_file.writeframes(pcm_data)
        frame_count += len(pcm_data) // (args.channels * 2)

    try:
        print("\n" + "=" * 60)
        print("PipeWire Native API Audio Capture (Ultra-Low Latency)")
        print("=" * 60)
        print(f"Target PID:     {pid}")
        print(f"Output file:    {output_path}")
        print(f"Duration:       {args.duration} seconds")
        print(f"Sample rate:    {args.sample_rate} Hz")
        print(f"Channels:       {args.channels}")
        print(f"Latency:        ~2-5ms (native API)")
        print("=" * 60)

        # Create LinuxBackend with explicit pipewire-native engine
        print("\nInitializing PipeWire Native API...")
        backend = LinuxBackend(
            pid=pid,
            sample_rate=args.sample_rate,
            channels=args.channels,
            sample_width=2,  # 16-bit
            engine="pipewire-native"
        )

        # Set up callback
        original_read = backend.read

        def read_wrapper(timeout: float = 0.1):
            data = original_read(timeout)
            if data:
                frames = len(data) // (args.channels * 2)
                on_audio_data(data, frames)
            return data

        backend.read = read_wrapper  # type: ignore

        print("Starting audio capture...")
        print("\n⚠️  IMPORTANT: Make sure the target process is actively playing audio!")
        print("⚠️  The capture may fail if the process is not producing audio.\n")

        backend.start()

        # Record for specified duration
        print(f"Recording for {args.duration} seconds...")
        start_time = time.time()
        while time.time() - start_time < args.duration:
            backend.read(timeout=0.01)  # Read with minimal timeout for low latency
            time.sleep(0.001)  # Yield CPU briefly

        # Stop capture
        print("\nStopping capture...")
        backend.stop()
        backend.close()

        # Close WAV file
        wav_file.close()

        # Show results
        duration = frame_count / args.sample_rate
        file_size = output_path.stat().st_size

        print("\n" + "=" * 60)
        print("Capture Complete!")
        print("=" * 60)
        print(f"Frames captured:  {frame_count:,}")
        print(f"Duration:         {duration:.2f} seconds")
        print(f"File size:        {file_size:,} bytes ({file_size / 1024:.1f} KB)")
        print(f"Output file:      {output_path.absolute()}")
        print("=" * 60)

        if frame_count == 0:
            print("\n⚠️  WARNING: No audio data was captured!")
            print("   Possible reasons:")
            print("   - The process is not currently playing audio")
            print("   - The process does not have PipeWire audio nodes")
            print("   - PipeWire daemon is not running")
            print("\n   Try:")
            print("   1. Make sure the process is actively playing audio")
            print("   2. Check 'pw-cli ls Node' to see active nodes")
            print("   3. Verify PipeWire is running: 'systemctl --user status pipewire'")
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        wav_file.close()
        return 130

    except Exception as e:
        print(f"\nError during capture: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        wav_file.close()
        return 1


if __name__ == '__main__':
    sys.exit(main())
