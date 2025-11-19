#!/usr/bin/env python3.12
"""Direct test of AudioHardwareCreateAggregateDevice with ctypes."""

import sys
import logging
import uuid

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, "src")

from proctap.backends import macos_coreaudio_ctypes as ca_ctypes

print("Testing AudioHardwareCreateAggregateDevice with ctypes...")
print("=" * 70)

# Test: Create minimal aggregate device
print("\nCreating minimal aggregate device...")

# Minimal description (just UID and name)
py_dict = {
    "uid": f"test-minimal-{uuid.uuid4()}",
    "name": "Test Minimal Device",
    "private": True,
    "stacked": False,
}

print(f"Description (Python): {py_dict}")

try:
    # Convert to CFDictionary
    print("\nConverting to CFDictionary...")
    cf_dict = ca_ctypes.create_cf_dictionary(py_dict)
    print(f"✓ CFDictionary created: {cf_dict}")

    # Call AudioHardwareCreateAggregateDevice
    print("\nCalling AudioHardwareCreateAggregateDevice...")
    print("(This may crash if function signature is wrong)")

    status, device_id = ca_ctypes.AudioHardwareCreateAggregateDevice(cf_dict)

    print(f"✓ Function returned!")
    print(f"  Status: {status}")
    print(f"  Device ID: {device_id}")

    # Release CFDictionary
    ca_ctypes.CFRelease(cf_dict)

    if status == 0 and device_id != 0:
        print(f"\n✅ SUCCESS: Created aggregate device {device_id}")

        # Clean up
        print("\nCleaning up...")
        cleanup_status = ca_ctypes.AudioHardwareDestroyAggregateDevice(device_id)
        print(f"✓ Cleanup status: {cleanup_status}")
    else:
        print(f"\n⚠️  Function succeeded but returned error: status={status}, device_id={device_id}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("Test completed (no crash!)")
