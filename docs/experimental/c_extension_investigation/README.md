# macOS C Extension Investigation (Archived)

**Date**: 2025-11-18
**Status**: Archived - API unavailability confirmed

## Overview

This directory contains the investigation and refactoring work for the macOS C extension backend using Core Audio Process Tap API.

## Investigation Summary

All three macOS backend implementations (Swift CLI, C Extension, PyObjC) failed due to the `kAudioHardwarePropertyTranslatePIDToProcessObject` API being unavailable on macOS 14.6 (Darwin 24.6.0).

### Key Findings

1. **Aggregate Device Approach (Original)**:
   - Process Tap created successfully (tapID=118)
   - Aggregate Device created successfully (device_id=120)
   - IOProc invoked but received `inBuffers=0, outBuffers=1`
   - Result: 0 bytes captured

2. **Direct Tap Approach (Refactored)**:
   - Removed all Aggregate Device code
   - Attached IOProc directly to Process Tap
   - Architecturally correct implementation
   - Result: Blocked by PID→AudioObjectID translation API unavailability

3. **PyObjC Backend**:
   - Never used Aggregate Device (correct from the start)
   - Also blocked by the same API unavailability

## Files in This Archive

- **FINDINGS.md** - Comprehensive investigation report with timeline
- **DEBUG_LOG.md** - Detailed test logs showing Aggregate Device approach behavior
- **test_tap_direct.py** - Test script for direct tap attachment
- **debug_device_streams.py** - Script to query aggregate device stream configuration
- **test_native_simple.py** - Simple native backend test
- **test_native_backend.py** - Native backend integration test
- **fix_summary.md** - Summary of PID→AudioObjectID fix attempt

## Lessons Learned

### Correct Architecture

The correct approach for Process Tap API is:
```
Process Tap (tap_id) → IOProc (direct) → Ring Buffer → Python
```

NOT:
```
Process Tap → Aggregate Device → IOProc (wrong)
```

### API Requirements

Core Audio Process Tap API requires:
1. `kAudioHardwarePropertyTranslatePIDToProcessObject` for PID→AudioObjectID translation
2. `AudioHardwareCreateProcessTap` for tap creation
3. `AudioDeviceCreateIOProcID` for IOProc attachment
4. Process must be actively playing audio

### Implementation Status

- **Refactored C Extension**: Architecturally correct, compiles successfully
- **PID→AudioObjectID Fix**: Properly implemented with correct memory management
- **Functionality**: Blocked by macOS API unavailability

## Recommendation

❌ Do NOT continue with Process Tap API approach

✅ Alternative Solutions:
1. **BlackHole + Loopback Audio** - Proven, reliable, works on all macOS versions
2. **Screen Capture Kit Audio** (macOS 13+) - Official API with process isolation
3. **AudioServerPlugin** - Low-level but complex
4. **Virtual Audio Devices** - Redirect per-process via Multi-Output Device

## Related Commits

- `d79b26a` - Adopted PyObjC as official backend
- Current refactoring work (not committed)

## Code Location

The refactored C extension is at:
- `src/proctap/_native_macos.m` (current - may be reverted)
- `src/proctap/experimental/_native_macos.m` (backup of refactored version)
