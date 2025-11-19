#!/usr/bin/env python3.12
"""Check which Core Audio functions are available in PyObjC."""

import sys
sys.path.insert(0, "src")

try:
    from CoreAudio import *
    import CoreAudio

    print("CoreAudio module attributes:")
    print("=" * 70)

    # List all functions that contain "Aggregate"
    aggregate_funcs = [name for name in dir(CoreAudio) if 'Aggregate' in name]
    print(f"\nAggregate-related functions ({len(aggregate_funcs)}):")
    for name in sorted(aggregate_funcs):
        obj = getattr(CoreAudio, name)
        print(f"  {name}: {type(obj)}")

    # Check specific functions
    print("\n" + "=" * 70)
    print("Checking specific functions:")

    funcs_to_check = [
        'AudioHardwareCreateAggregateDevice',
        'AudioHardwareDestroyAggregateDevice',
        'AudioHardwareCreateProcessTap',
        'AudioHardwareDestroyProcessTap',
        'AudioDeviceCreateIOProcID',
        'AudioDeviceStart',
        'AudioDeviceStop',
    ]

    for func_name in funcs_to_check:
        if hasattr(CoreAudio, func_name):
            func = getattr(CoreAudio, func_name)
            print(f"✓ {func_name}: {type(func)}")

            # Try to get function signature
            if hasattr(func, '__metadata__'):
                print(f"    Metadata: {func.__metadata__}")
        else:
            print(f"✗ {func_name}: NOT FOUND")

except ImportError as e:
    print(f"ERROR: Failed to import CoreAudio: {e}")
    sys.exit(1)
