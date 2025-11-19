#!/usr/bin/env python3.12
"""Test audio capture with detailed logging."""

import sys
import logging
import time

sys.path.insert(0, 'src')

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

from proctap.backends.macos_pyobjc import MacOSNativeBackend

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_with_logging.py <PID>")
        return 1

    pid = int(sys.argv[1])
    print(f'\n🧪 Testing Audio Capture with PID {pid}')
    print('='*70)
    print()

    try:
        print("Creating backend...")
        backend = MacOSNativeBackend(pid, 48000, 2, 2)

        print("Starting capture...")
        backend.start()

        print(f"Capturing for 5 seconds...")
        print(f"(Watch for '🎵 IOProc callback' messages)")
        print()

        time.sleep(5)

        print()
        print("Reading captured data...")
        chunk_count = 0
        total_bytes = 0

        while True:
            chunk = backend.read()
            if chunk:
                chunk_count += 1
                total_bytes += len(chunk)
                if chunk_count <= 3:
                    print(f"  Read chunk #{chunk_count}: {len(chunk)} bytes")
            else:
                break

        print()
        print("Stopping capture...")
        backend.stop()

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
        else:
            print()
            print('❌ FAILED: No audio captured')
            print()
            print('This means IOProc callback was never called.')

        return 0 if total_bytes > 0 else 1

    except Exception as e:
        print(f'\n❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
