#!/usr/bin/env python3.12
"""Verify aggregate device configuration."""

import sys
sys.path.insert(0, 'src')

from proctap.backends.macos_pyobjc import ProcessAudioDiscovery, MacOSNativeBackend
import logging

logging.basicConfig(level=logging.INFO)

def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_aggregate_device.py <PID>")
        return 1

    pid = int(sys.argv[1])
    print(f'\n🔍 Verifying Aggregate Device for PID {pid}')
    print('='*70)

    try:
        # Create backend
        backend = MacOSNativeBackend(pid, 48000, 2, 2)

        # Start (this creates aggregate device)
        backend.start()

        print()
        print(f'✓ Aggregate device created: ID {backend._aggregate_device_id}')
        print(f'✓ Tap device ID: {backend._tap_device_id}')
        print(f'✓ IOProc ID: {backend._io_proc_id}')
        print()

        # Try to read aggregate device properties
        from CoreAudio import (
            AudioObjectGetPropertyData,
            AudioObjectPropertyAddress,
            kAudioObjectPropertyScopeGlobal,
            kAudioObjectPropertyElementMain
        )

        # Read sub-device list
        print("Checking aggregate device configuration...")

        # kAudioAggregateDevicePropertyFullSubDeviceList = 'apsd'
        try:
            address = AudioObjectPropertyAddress(
                mSelector=0x61707364,  # 'apsd'
                mScope=kAudioObjectPropertyScopeGlobal,
                mElement=kAudioObjectPropertyElementMain
            )

            status, size, data = AudioObjectGetPropertyData(
                backend._aggregate_device_id,
                address,
                0, None, 0, None
            )
            print(f"  Sub-device list size query: status={status}, size={size}")
        except Exception as e:
            print(f"  Could not read sub-device list: {e}")

        # Keep running for a bit to see if callbacks come
        import time
        print()
        print("Waiting 3 seconds for callbacks...")
        time.sleep(3)

        # Check if any data arrived
        chunk_count = 0
        while True:
            chunk = backend.read()
            if chunk:
                chunk_count += 1
            else:
                break

        print(f"Chunks received: {chunk_count}")

        backend.stop()

        return 0

    except Exception as e:
        print(f'\n❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
