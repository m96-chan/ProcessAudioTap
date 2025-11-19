# macOS Backend Version Comparison

## Timeline and Architecture Analysis

### Commit 8d78147 (2025-11-17) - Swift CLI Backend
**File**: `src/proctap/backends/macos.py` (Swift helper subprocess)
**Swift**: `swift/proctap-macos/Sources/main.swift`

**Architecture**:
```
PID → AudioObjectID (via kAudioHardwarePropertyTranslatePIDToProcessObject)
  ↓
Process Tap Creation
  ↓
Aggregate Device Creation (with tap)
  ↓
IOProc Attachment (to aggregate device)
  ↓
Audio Capture
```

**Key Code** (Swift):
```swift
// Line 135-145: PID → ProcessObject translation
let status = AudioObjectGetPropertyData(
    AudioObjectID(kAudioObjectSystemObject),
    &AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyTranslatePIDToProcessObject,
        ...
    ),
    ...
    &processObject
)

// Line 95-96: Aggregate Device approach
device = try createAggregateDevice(with: tap)
```

**Status**: "Implemented for macOS 14.4+"

---

### Commit ef3cc65 (2025-11-17) - PyObjC Prototype
**File**: `src/proctap/backends/macos_pyobjc.py` (initial prototype)

**Architecture**: Phase 1 - Process Discovery Only
- Only implemented PID → AudioObjectID translation
- No actual audio capture implemented yet

**Status**: "Phase 1 - Prototype Implementation"

---

### Commit d79b26a (2025-11-18) - PyObjC Official Backend
**File**: `src/proctap/backends/macos_pyobjc.py` (full implementation)

**Architecture**:
```
PID → AudioObjectID (via kAudioHardwarePropertyTranslatePIDToProcessObject)
  ↓
Process Tap Creation (CATapDescription with AudioObjectID)
  ↓
IOProc Attachment (DIRECTLY to tap_device_id, NO aggregate device!)
  ↓
Audio Capture
```

**Key Code** (Python/ctypes):
```python
# Line 454-488: PID → ProcessObject translation
status = _AudioObjectGetPropertyData(
    kAudioObjectSystemObject,
    byref(address),  # kAudioHardwarePropertyTranslatePIDToProcessObject
    ...
    byref(process_object_id)
)

# Line 636-657: Direct tap attachment (NO aggregate device!)
self._tap_device_id = create_process_tap(self._process_object_id, ...)
status = _AudioDeviceCreateIOProcID(
    self._tap_device_id,  # Direct to tap!
    self._io_callback,
    ...
)
status = _AudioDeviceStart(self._tap_device_id, ...)
```

**Status**: "Phase 3 - Official macOS Backend (Verified Working)"
- ⚠️ This "Verified Working" claim is **questionable**
- No test logs or evidence of actual audio capture

---

### Current Investigation (2025-11-18) - C Extension Refactoring

**Original C Extension** (Aggregate Device approach):
- File: `src/proctap/experimental/_native_macos.m` (at d79b26a)
- Used Aggregate Device (same as Swift CLI)
- **Test Results**:
  - ✅ Tap ID: 118 created
  - ✅ Aggregate Device ID: 120 created
  - ✅ IOProc invoked
  - ❌ `inBuffers=0, outBuffers=1` (no input streams)
  - ❌ 0 bytes captured

**Refactored C Extension** (Direct tap approach):
- File: `src/proctap/_native_macos.m` (refactored, not committed)
- Removed Aggregate Device
- Attached IOProc directly to tap (same architecture as PyObjC)
- **Test Results**:
  - ❌ PID→AudioObjectID translation fails
  - ❌ `kAudioHardwarePropertyTranslatePIDToProcessObject` API unavailable

---

## API Availability Analysis

### `kAudioHardwarePropertyTranslatePIDToProcessObject` ('pid2')

**Used by**:
- Swift CLI (8d78147)
- PyObjC Backend (d79b26a)
- C Extension (all versions)

**Test Results on macOS 14.6 (Darwin 24.6.0)**:
| Implementation | API Call Result | Notes |
|----------------|-----------------|-------|
| Swift CLI | Returns `noErr` but `tapID=0` | Invalid tap created |
| PyObjC | `AudioObjectHasProperty` returns False | Property not available |
| C Extension (refactored) | Translation fails, returns error | Same as PyObjC |
| C Extension (Aggregate) | Successfully created tap/device but 0 bytes | API worked but capture failed |

### Discrepancy

**Critical Question**: Why does the C Extension with Aggregate Device successfully create tap (tapID=118) but the refactored version fails at PID→AudioObjectID translation?

**Hypothesis**:
1. The Aggregate Device version might be using cached/old compiled binary
2. The Swift CLI binary might be pre-compiled from a different macOS version
3. The API might be intermittently available or require specific conditions

---

## Architecture Comparison

### Aggregate Device Approach (Swift CLI, Old C Extension)
```
Process → kAudioHardwarePropertyTranslatePIDToProcessObject → AudioObjectID
          ↓
       CATapDescription(AudioObjectID) → AudioHardwareCreateProcessTap
          ↓
       Create Aggregate Device (with tap UUID)
          ↓
       AudioDeviceCreateIOProcID(aggregate_device_id)
          ↓
       AudioDeviceStart(aggregate_device_id)
          ↓
       IOProc receives: inBuffers=0, outBuffers=1 ❌
```

**Problem**: Aggregate device has no input streams from tap

### Direct Tap Approach (PyObjC, Refactored C Extension)
```
Process → kAudioHardwarePropertyTranslatePIDToProcessObject → AudioObjectID ❌
          ↓
       (BLOCKED - API unavailable)
```

**Problem**: Cannot translate PID to AudioObjectID

---

## Conclusion

### All Three Implementations Use the Same Broken Approach

1. **Swift CLI** (8d78147):
   - Uses `kAudioHardwarePropertyTranslatePIDToProcessObject` ✅ (somehow works?)
   - Uses Aggregate Device ❌ (wrong architecture)
   - Result: Unknown (needs testing at that commit)

2. **PyObjC** (d79b26a):
   - Uses `kAudioHardwarePropertyTranslatePIDToProcessObject` ❌ (API unavailable)
   - Uses Direct Tap Attachment ✅ (correct architecture)
   - Result: Fails at PID translation

3. **C Extension** (current):
   - Original: Uses Aggregate Device, gets 0 bytes
   - Refactored: Fails at PID translation

### Recommendation

**Test commit 8d78147 Swift CLI** to determine:
1. Does it actually capture audio?
2. If yes, what's different about that environment/build?
3. If no, was it ever actually verified working?

**Alternative**: The entire Process Tap API approach may be fundamentally unavailable on this macOS version (14.6), despite Apple's documentation claiming 14.4+ support.
