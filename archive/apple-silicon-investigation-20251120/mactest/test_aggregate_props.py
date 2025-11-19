#!/usr/bin/env python3.12
"""Test aggregate device properties to verify configuration."""

import sys
sys.path.insert(0, 'src')

from proctap.backends.macos_pyobjc import ProcessAudioDiscovery, MacOSNativeBackend
from proctap.backends import macos_coreaudio_ctypes as ca_ctypes
from CoreAudio import (
    AudioObjectGetPropertyData,
    AudioObjectPropertyAddress,
    kAudioObjectPropertyScopeGlobal,
    kAudioObjectPropertyElementMain
)
import logging

logging.basicConfig(level=logging.INFO)

def test_aggregate_device(pid: int):
    print(f'\n🔍 Testing Aggregate Device for PID {pid}')
    print('='*70)

    # Create backend
    backend = MacOSNativeBackend(pid, 48000, 2, 2)
    backend.start()

    print()
    print(f'✓ Aggregate device ID: {backend._aggregate_device_id}')
    print(f'✓ Tap device ID: {backend._tap_device_id}')
    print(f'✓ IOProc ID: {backend._io_proc_id}')
    print()

    # Check if aggregate device is active
    print("Checking aggregate device properties...")

    # Try reading device name
    selector_name = 0x6E616D65  # 'name'
    address = AudioObjectPropertyAddress(
        mSelector=selector_name,
        mScope=kAudioObjectPropertyScopeGlobal,
        mElement=kAudioObjectPropertyElementMain
    )

    try:
        status, size, data = AudioObjectGetPropertyData(
            backend._aggregate_device_id,
            address,
            0, None, 0, None
        )
        print(f"  Device name query: status={status}, size={size}")
        if status == 0:
            print(f"    Name: {data}")
    except Exception as e:
        print(f"  Could not read device name: {e}")

    # Check if device is running
    selector_running = 0x67727764  # 'grwd' (kAudioDevicePropertyDeviceIsRunning)
    address_running = AudioObjectPropertyAddress(
        mSelector=selector_running,
        mScope=kAudioObjectPropertyScopeGlobal,
        mElement=kAudioObjectPropertyElementMain
    )

    try:
        status, size, data = AudioObjectGetPropertyData(
            backend._aggregate_device_id,
            address_running,
            0, None, 0, None
        )
        print(f"  Device running query: status={status}, size={size}, data={data}")
    except Exception as e:
        print(f"  Could not check if device is running: {e}")

    # Wait a bit
    import time
    print()
    print("Waiting 3 seconds...")
    time.sleep(3)

    # Check callbacks
    chunk_count = 0
    while True:
        chunk = backend.read()
        if chunk:
            chunk_count += 1
        else:
            break

    print(f"Chunks received: {chunk_count}")

    backend.stop()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_aggregate_props.py <PID>")
        sys.exit(1)

    pid = int(sys.argv[1])
    test_aggregate_device(pid)
