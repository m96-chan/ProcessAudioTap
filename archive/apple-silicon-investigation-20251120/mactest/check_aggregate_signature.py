#!/usr/bin/env python3.12
"""Check AudioHardwareCreateAggregateDevice signature."""

import sys
sys.path.insert(0, "src")

from CoreAudio import AudioHardwareCreateAggregateDevice
import objc

print("AudioHardwareCreateAggregateDevice function signature:")
print("=" * 70)

# Get metadata
metadata = AudioHardwareCreateAggregateDevice.__metadata__()
print(f"Metadata: {metadata}")
print()

# Get signature
if hasattr(AudioHardwareCreateAggregateDevice, '__signature__'):
    print(f"Signature: {AudioHardwareCreateAggregateDevice.__signature__}")

# Get callable signature
print(f"Callable: {callable(AudioHardwareCreateAggregateDevice)}")

# Try to get more details
print(f"\nFunction attributes:")
for attr in dir(AudioHardwareCreateAggregateDevice):
    if not attr.startswith('_'):
        value = getattr(AudioHardwareCreateAggregateDevice, attr)
        print(f"  {attr}: {value}")

# Check if it needs explicit metadata specification
print("\n" + "=" * 70)
print("Attempting to call with minimal args...")

test_dict = {
    b'uid': 'test-uid-12345',  # Try bytes key
    b'name': 'Test Device',
}

print(f"Test dict: {test_dict}")

try:
    result = AudioHardwareCreateAggregateDevice(test_dict, None)
    print(f"Result: {result}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
