#!/usr/bin/env python3.12
"""Minimal test for AudioHardwareCreateAggregateDevice."""

import sys
import logging
import uuid

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, "src")

from proctap.backends.macos_pyobjc import (
    AudioHardwareCreateAggregateDevice,
    kAudioAggregateDeviceUIDKey,
    kAudioAggregateDeviceNameKey,
    kAudioAggregateDeviceSubDeviceListKey,
    kAudioAggregateDeviceMainSubDeviceKey,
    kAudioAggregateDeviceTapListKey,
    kAudioAggregateDeviceTapAutoStartKey,
    kAudioAggregateDeviceIsPrivateKey,
    kAudioAggregateDeviceIsStackedKey,
    kAudioSubDeviceUIDKey,
    kAudioSubTapUIDKey,
    kAudioSubTapDriftCompensationKey,
)

print("Testing AudioHardwareCreateAggregateDevice...")

# Test 1: Empty aggregate device (no tap, no sub-devices)
print("\nTest 1: Creating minimal aggregate device (no tap, no sub-devices)")
try:
    minimal_desc = {
        kAudioAggregateDeviceUIDKey: f"test-minimal-{uuid.uuid4()}",
        kAudioAggregateDeviceNameKey: "Test Minimal",
        kAudioAggregateDeviceIsPrivateKey: True,
        kAudioAggregateDeviceIsStackedKey: False,
    }

    print(f"Description: {minimal_desc}")
    status, device_id = AudioHardwareCreateAggregateDevice(minimal_desc, None)

    if status == 0 and device_id != 0:
        print(f"✅ SUCCESS: Created device ID {device_id}")

        # Clean up
        from proctap.backends.macos_pyobjc import AudioHardwareDestroyAggregateDevice
        AudioHardwareDestroyAggregateDevice(device_id)
        print("✅ Cleaned up device")
    else:
        print(f"❌ FAILED: status={status}, device_id={device_id}")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\nTest completed!")
