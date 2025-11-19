# Final Conclusion: macOS Process Tap API Investigation

## Executive Summary

**Result**: All macOS backend implementations (Swift CLI, C Extension, PyObjC) are **non-functional** on macOS 14.6 (Darwin 24.6.0).

**Root Cause**: The Core Audio Process Tap API is either:
1. Not fully implemented in macOS 14.6
2. Requires undocumented permissions/entitlements
3. Has incompatible SDK definitions across macOS versions
4. Was never actually tested and verified working

## Evidence

### 1. Swift CLI (commits 8d78147, d1f53b0)

**Compilation Status**: ❌ FAILED

**Errors**:
```
error: value of type 'CATapDescription' has no member 'mIncludeProcesses'
error: value of type 'CATapDescription' has no member 'mProcessingType'
error: cannot find 'kAudioTapProcessingTypeMixDown' in scope
error: value of type 'CATapDescription' has no member 'mMuteBehavior'
```

**Analysis**:
- Code assumes `CATapDescription` structure members that don't exist in current SDK
- API definitions changed between SDK versions or were never public
- **Cannot compile on current macOS 14.6 SDK**

### 2. PyObjC Backend (commit d79b26a)

**Status**: Marked as "Phase 3 - Official macOS Backend (Verified Working)" ⚠️

**Reality**:
- Documentation shows "Testing Requirements (Pending - Requires macOS 14.4+)"
- **No evidence of actual testing or verification**
- Uses `kAudioHardwarePropertyTranslatePIDToProcessObject` API
- API unavailable: `AudioObjectHasProperty` returns False

**Test Results**:
```python
has_property = _AudioObjectHasProperty(
    kAudioObjectSystemObject,
    byref(address)  # kAudioHardwarePropertyTranslatePIDToProcessObject
)
# Returns: False (property not available)
```

### 3. C Extension (Original with Aggregate Device)

**Status**: Creates devices successfully, captures 0 bytes

**Test Results**:
```
[DEBUG] Process tap created with ID: 118 ✅
[DEBUG] Aggregate device created successfully (ID: 119) ✅
[DEBUG] IOProcID created for aggregate device 119 ✅
[DEBUG] Aggregate device started successfully! ✅

[IOPROC] called #0: inBuffers=0 inBytes=0 outBuffers=1 ❌
[IOPROC] called #100: inBuffers=0 inBytes=0 outBuffers=1 ❌
[IOPROC] called #200: inBuffers=0 inBytes=0 outBuffers=1 ❌

Read 0 bytes ❌
```

**Analysis**:
- All CoreAudio APIs return `noErr` (success)
- Tap and Aggregate Device created successfully
- IOProc invoked but receives NO input buffers
- Aggregate Device approach is architecturally wrong

### 4. C Extension (Refactored, Direct Tap)

**Status**: Correct architecture, blocked by API unavailability

**Test Results**:
```
[DEBUG] create_process_tap: Starting...
[DEBUG] Converting PIDs to AudioObjectIDs...
Python error: Failed to create process tap:
```

**Analysis**:
- Code is architecturally correct (matches PyObjC approach)
- PID→AudioObjectID translation fails
- `kAudioHardwarePropertyTranslatePIDToProcessObject` API unavailable

## Timeline Analysis

| Date | Commit | Event | Status |
|------|--------|-------|--------|
| 2025-11-17 | ef3cc65 | PyObjC prototype created | "Phase 1 - Prototype" |
| 2025-11-17 | 8d78147 | Linux PipeWire work merged | Swift CLI present but not tested |
| 2025-11-18 | d1f53b0 | Merge from main | "Testing Pending" in docs |
| 2025-11-18 | d79b26a | PyObjC marked "Official" | "Verified Working" (unverified) |
| 2025-11-18 | Current | Investigation | All implementations fail |

## Critical Questions

### Q1: Was it ever actually working?

**Answer**: **Probably not.**

**Evidence**:
1. Documentation explicitly states "Testing Requirements (Pending)"
2. Swift CLI code doesn't compile on current SDK
3. No test logs or output demonstrating successful audio capture
4. All implementations depend on unavailable API

### Q2: Why was it marked "Verified Working"?

**Hypothesis**:
1. Optimistic assumption based on API documentation
2. Testing was planned but never executed
3. Confusion between "compiles/runs" vs "actually captures audio"
4. Process discovery working ≠ audio capture working

### Q3: Did SDK definitions change?

**Answer**: **Almost certainly yes.**

**Evidence**:
- `CATapDescription` structure members don't match code expectations
- `kAudioTapProcessingTypeMixDown` constant doesn't exist
- `kAudioHardwarePropertyTranslatePIDToProcessObject` unavailable

Apple may have:
1. Changed API definitions between macOS versions
2. Never publicly released these APIs
3. Deprecated the APIs after initial documentation

## Technical Analysis

### API Availability Matrix

| API | Expected | Actual | Status |
|-----|----------|--------|--------|
| `AudioHardwareCreateProcessTap` | Available (14.4+) | Returns noErr, tapID=0 (Swift) | ⚠️ Partial |
| `CATapDescription.mIncludeProcesses` | Structure member | Does not exist | ❌ Missing |
| `kAudioHardwarePropertyTranslatePIDToProcessObject` | Property selector | Not available | ❌ Missing |
| `kAudioTapProcessingTypeMixDown` | Constant | Does not exist | ❌ Missing |

### Architecture Comparison

**Wrong Approach** (Swift CLI, Old C Extension):
```
Process → PID→AudioObjectID → ProcessTap → AggregateDevice → IOProc
                                                    ↓
                                        No input streams! (0 bytes)
```

**Correct Approach** (PyObjC, Refactored C Extension):
```
Process → PID→AudioObjectID → ProcessTap → IOProc (direct)
             ↓
      API unavailable! (blocked)
```

**Both approaches fail**, but for different reasons.

## System Environment

- **macOS Version**: 14.6 (Darwin 24.6.0)
- **Architecture**: arm64 (Apple Silicon)
- **Xcode/SDK**: Current (as of 2025-11-18)
- **Expected Requirement**: macOS 14.4+ (Sonoma)

## Conclusion

### Primary Findings

1. **Process Tap API is not functional on macOS 14.6**
   - Critical APIs unavailable or incomplete
   - SDK definitions incompatible with documentation

2. **No implementation was ever verified working**
   - "Verified Working" status was premature
   - No test logs or evidence of successful capture

3. **All three approaches fail**:
   - Swift CLI: Doesn't compile
   - PyObjC: API unavailable
   - C Extension: 0 bytes (Aggregate) or API unavailable (Direct)

### Recommendations

**❌ DO NOT pursue Process Tap API approach**

**✅ Viable Alternatives:**

1. **BlackHole + Multi-Output Device**
   - Proven, stable, works on all macOS versions
   - Requires manual audio routing setup
   - Not truly per-process (system-wide routing)

2. **Screen Capture Kit (SCK) Audio API** (macOS 13+)
   - Official Apple API for process-specific capture
   - Designed for screen recording but includes audio
   - Requires app permissions
   - Reference: https://developer.apple.com/documentation/screencapturekit

3. **AudioServerPlugin**
   - Low-level Core Audio plugin
   - Can intercept audio at HAL level
   - Complex implementation, requires code signing

4. **Virtual Audio Devices**
   - Use Multi-Output Device + process-specific routing
   - Similar to BlackHole but more automated
   - Still not true per-process isolation

### Best Option: Screen Capture Kit

**Recommendation**: Implement Screen Capture Kit Audio backend

**Advantages**:
- Official Apple API (macOS 13+)
- Designed for per-process capture
- Well-documented and supported
- No undocumented APIs or hacks

**Implementation Approach**:
```swift
import ScreenCaptureKit

// 1. Get available content
let content = try await SCShareableContent.current

// 2. Filter for target process
let targetApp = content.applications.first { $0.processID == targetPID }

// 3. Create stream configuration
let config = SCStreamConfiguration()
config.capturesAudio = true
config.sampleRate = 48000
config.channelCount = 2

// 4. Create and start stream
let filter = SCContentFilter(desktopIndependentWindow: targetApp.mainWindow!)
let stream = SCStream(filter: filter, configuration: config, delegate: self)
try stream.addStreamOutput(self, type: .audio, sampleHandlerQueue: audioQueue)
try await stream.startCapture()
```

## Archive Purpose

This investigation is archived in `docs/experimental/c_extension_investigation/` as:
- **Historical record** of Process Tap API investigation
- **Reference** for future macOS audio capture work
- **Evidence** that Process Tap API is not viable on macOS 14.6
- **Lesson learned**: Always verify API availability before claiming "Verified Working"

## Next Steps

1. ✅ Archive investigation (completed)
2. ⏭️ Research Screen Capture Kit Audio implementation
3. ⏭️ Prototype SCK backend for ProcTap
4. ⏭️ Update documentation to reflect SCK as official macOS backend
5. ⏭️ Mark Process Tap approaches as experimental/deprecated

---

**Date**: 2025-11-18
**Investigator**: Claude Code + m96-chan
**System**: macOS 14.6 (Darwin 24.6.0), arm64
