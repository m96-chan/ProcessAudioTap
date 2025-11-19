#!/usr/bin/env python3.12
"""Test the new C extension with Chrome audio."""

import sys
import time

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_c_extension.py <PID>")
        return 1

    pid = int(sys.argv[1])

    print(f'\n🧪 Testing C Extension with PID {pid}')
    print('='*70)
    print()

    try:
        # Import the native extension
        from proctap._macos_native import ProcessTap

        print("✓ Native extension loaded successfully")
        print()

        # Create ProcessTap object
        print(f"Creating ProcessTap for PID {pid}...")
        tap = ProcessTap(pid, 48000, 2, 16)
        print("✓ ProcessTap object created")
        print()

        # Start capture
        print("Starting audio capture...")
        tap.start()
        print("✓ Audio capture started")
        print()

        # Capture for 5 seconds
        print("Capturing for 5 seconds...")
        time.sleep(5)
        print()

        # Read captured data
        print("Reading captured data...")
        chunk_count = 0
        total_bytes = 0

        while True:
            chunk = tap.read()
            if chunk is None:
                break
            chunk_count += 1
            total_bytes += len(chunk)
            if chunk_count <= 3:
                print(f"  Chunk #{chunk_count}: {len(chunk)} bytes")

        print()
        print("Stopping capture...")
        tap.stop()
        print("✓ Capture stopped")
        print()

        print('='*70)
        print(f'📊 Results:')
        print(f'  Chunks captured: {chunk_count}')
        print(f'  Total bytes: {total_bytes:,}')
        print()

        if total_bytes > 0:
            duration = total_bytes / (48000 * 2 * 2)  # sample_rate * channels * bytes_per_sample
            print(f'  Estimated duration: {duration:.2f} seconds')
            print()
            print('✅ SUCCESS: Audio captured!')
            return 0
        else:
            print()
            print('❌ FAILED: No audio captured')
            return 1

    except Exception as e:
        print(f'\n❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
