#!/usr/bin/env python3.12
"""
Detailed test of Aggregate Device creation following AudioCap architecture.

This script tests each step of the Process Tap + Aggregate Device setup:
1. Process discovery (PID → AudioObjectID)
2. Process Tap creation
3. Tap stream format reading (CRITICAL - must be done before aggregate)
4. Aggregate Device creation with:
   - System output device as sub-device
   - Process Tap in tap list
5. IOProc attachment to Aggregate Device
6. Device start and audio capture

Usage:
    # Start a process that plays audio, then:
    python3.12 test_aggregate_device.py <PID>

    # Or use the 'say' command:
    say 'Testing audio capture' & python3.12 test_aggregate_device.py $!
"""

import sys
import time
import logging
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from proctap.backends.macos_pyobjc import (
    MacOSNativeBackend,
    ProcessAudioDiscovery,
    get_default_output_device_uid,
    is_available,
    supports_process_tap,
    get_macos_version
)

def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def test_prerequisites():
    """Test that all prerequisites are met."""
    print_section("PREREQUISITES CHECK")

    # Check macOS version
    major, minor, patch = get_macos_version()
    print(f"✓ macOS Version: {major}.{minor}.{patch}")

    if not supports_process_tap():
        print(f"✗ ERROR: macOS {major}.{minor}.{patch} does not support Process Tap API")
        print("  Requires macOS 14.4 (Sonoma) or later")
        return False

    # Check PyObjC availability
    if not is_available():
        print("✗ ERROR: PyObjC Core Audio not available")
        print("  Install with: pip install pyobjc-core pyobjc-framework-CoreAudio")
        return False

    print("✓ PyObjC Core Audio: Available")

    # Get default output device
    try:
        output_uid = get_default_output_device_uid()
        print(f"✓ Default Output Device UID: {output_uid}")
    except Exception as e:
        print(f"✗ ERROR: Failed to get output device: {e}")
        return False

    print("\n✅ All prerequisites met!")
    return True

def test_process_discovery(pid: int):
    """Test process audio discovery."""
    print_section("STEP 1: PROCESS DISCOVERY")

    try:
        discovery = ProcessAudioDiscovery()
        print(f"Checking PID {pid} for audio output...")

        has_audio = discovery.find_process_with_audio(pid)

        if has_audio:
            object_id = discovery.get_process_object_id(pid)
            print(f"✓ Process {pid} has audio output")
            print(f"✓ AudioObjectID: {object_id}")
            print("\n✅ Process discovery: SUCCESS")
            return True
        else:
            print(f"✗ Process {pid} does not have active audio output")
            print("\n⚠️  Make sure the process is actively playing audio!")
            return False

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_capture(pid: int, duration: float = 3.0):
    """Test full capture flow including Aggregate Device."""
    print_section("STEP 2-6: FULL CAPTURE FLOW")

    try:
        print("Creating MacOSNativeBackend...")
        backend = MacOSNativeBackend(
            pid=pid,
            sample_rate=48000,
            channels=2,
            sample_width=2
        )
        print("✓ Backend instance created\n")

        print("Starting capture (this will test all steps):")
        print("  1. Process object ID lookup")
        print("  2. CATapDescription creation")
        print("  3. Process Tap creation")
        print("  4. Tap stream format reading ⚠️ CRITICAL")
        print("  5. Aggregate Device creation")
        print("  6. IOProc attachment to Aggregate Device")
        print("  7. Device start\n")

        backend.start()
        print("\n✅ Capture started successfully!\n")

        print(f"Reading audio for {duration} seconds...")
        print("(Watch for 'IOProc callback' messages in debug output)\n")

        start_time = time.time()
        total_bytes = 0
        chunks = 0
        last_report = start_time

        while time.time() - start_time < duration:
            data = backend.read()
            if data:
                total_bytes += len(data)
                chunks += 1

                # Progress report every 0.5 seconds
                now = time.time()
                if now - last_report >= 0.5:
                    elapsed = now - start_time
                    rate_kbps = (total_bytes / 1024) / elapsed if elapsed > 0 else 0
                    print(f"  [{elapsed:.1f}s] Chunks: {chunks:4d}, "
                          f"Bytes: {total_bytes:8,}, "
                          f"Rate: {rate_kbps:.1f} KB/s")
                    last_report = now

            time.sleep(0.01)  # 10ms polling

        print(f"\nStopping capture...")
        backend.stop()
        print("✓ Capture stopped\n")

        # Summary
        print(f"{'─'*70}")
        print(f"CAPTURE SUMMARY:")
        print(f"  Duration:     {duration:.2f} seconds")
        print(f"  Total Chunks: {chunks}")
        print(f"  Total Bytes:  {total_bytes:,}")

        if total_bytes > 0:
            avg_chunk_size = total_bytes / chunks if chunks > 0 else 0
            expected_bytes = 48000 * 2 * 2 * duration  # 48kHz, 2ch, 2 bytes/sample
            capture_ratio = (total_bytes / expected_bytes) * 100 if expected_bytes > 0 else 0

            print(f"  Avg Chunk:    {avg_chunk_size:.0f} bytes")
            print(f"  Capture Rate: {capture_ratio:.1f}% of expected")
            print(f"{'─'*70}")
            print("\n✅✅✅ SUCCESS: Aggregate Device is working! ✅✅✅")
            return True
        else:
            print(f"{'─'*70}")
            print("\n⚠️  WARNING: No audio data captured")
            print("\nPossible reasons:")
            print("  • Process stopped playing audio during capture")
            print("  • IOProc callback not receiving data (check debug logs)")
            print("  • Aggregate Device not properly configured")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3.12 test_aggregate_device.py <PID>")
        print("\nExample with 'say' command:")
        print("  say 'Testing audio capture for five seconds' & python3.12 test_aggregate_device.py $!")
        print("\nExample with Music.app:")
        print("  # Start playing music, then:")
        print("  pgrep -f Music | head -1 | xargs python3.12 test_aggregate_device.py")
        return 1

    try:
        pid = int(sys.argv[1])
    except ValueError:
        print(f"ERROR: Invalid PID: {sys.argv[1]}")
        return 1

    print("\n" + "="*70)
    print("  AudioCap-Style Aggregate Device Test")
    print("  Testing: Process Tap + Aggregate Device + IOProc")
    print("="*70)

    # Run tests
    if not test_prerequisites():
        return 1

    if not test_process_discovery(pid):
        return 1

    if not test_full_capture(pid, duration=3.0):
        return 1

    print_section("🎉 ALL TESTS PASSED! 🎉")
    print("The Aggregate Device implementation is working correctly!")
    print("AudioCap architecture successfully replicated in Python/PyObjC.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
