#!/usr/bin/env python3.12
"""Check the actual values of Core Audio aggregate device keys."""

import sys
sys.path.insert(0, "src")

from CoreAudio import (
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

print("Core Audio Aggregate Device Keys:")
print("=" * 70)

keys = [
    ("kAudioAggregateDeviceUIDKey", kAudioAggregateDeviceUIDKey),
    ("kAudioAggregateDeviceNameKey", kAudioAggregateDeviceNameKey),
    ("kAudioAggregateDeviceSubDeviceListKey", kAudioAggregateDeviceSubDeviceListKey),
    ("kAudioAggregateDeviceMainSubDeviceKey", kAudioAggregateDeviceMainSubDeviceKey),
    ("kAudioAggregateDeviceTapListKey", kAudioAggregateDeviceTapListKey),
    ("kAudioAggregateDeviceTapAutoStartKey", kAudioAggregateDeviceTapAutoStartKey),
    ("kAudioAggregateDeviceIsPrivateKey", kAudioAggregateDeviceIsPrivateKey),
    ("kAudioAggregateDeviceIsStackedKey", kAudioAggregateDeviceIsStackedKey),
    ("kAudioSubDeviceUIDKey", kAudioSubDeviceUIDKey),
    ("kAudioSubTapUIDKey", kAudioSubTapUIDKey),
    ("kAudioSubTapDriftCompensationKey", kAudioSubTapDriftCompensationKey),
]

for name, value in keys:
    if isinstance(value, bytes):
        decoded = value.decode('utf-8')
        print(f"{name:45s} = b'{value.decode('utf-8')}' ({decoded})")
    else:
        print(f"{name:45s} = {value} (type: {type(value)})")
