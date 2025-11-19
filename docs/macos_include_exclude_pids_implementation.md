# macOS Core Audio Process Tap - Include/Exclude PIDs Implementation

**Date:** 2025-11-18
**Status:** ✅ Completed
**Related Issue:** User request for advanced PID filtering

## Summary

Implemented advanced PID filtering for the macOS Core Audio Process Tap backend, allowing users to capture audio from multiple specific processes or exclude specific processes from capture.

## Features Implemented

### 1. Swift CLI Helper Enhancements

**File:** `swift/proctap-macos/Sources/main.swift`

#### New Command-Line Arguments

- `--include-pids <PIDs>`: Comma-separated list of PIDs to capture audio from
- `--exclude-pids <PIDs>`: Comma-separated list of PIDs to exclude from capture
- `--pid <PID>`: Legacy single PID support (converted to `--include-pids` internally)

#### Core Audio Integration

- Implemented PID to AudioObjectID translation using `kAudioHardwarePropertyTranslatePIDToProcessObject`
- Used `CATapDescription` Objective-C initializers:
  - `initStereoMixdownOfProcesses:` - Capture from specific processes (stereo)
  - `initMonoMixdownOfProcesses:` - Capture from specific processes (mono)
  - `initStereoGlobalTapButExcludeProcesses:` - Capture all except specified (stereo)
  - `initMonoGlobalTapButExcludeProcesses:` - Capture all except specified (mono)

#### Key Implementation Details

```swift
// Convert PIDs to AudioObjectIDs
var includeObjects: [AudioObjectID] = []
for pid in includePIDs {
    let obj = try getProcessObject(for: pid)
    includeObjects.append(obj)
}

// Create tap description based on configuration
if !excludeProcesses.isEmpty {
    tapDesc = CATapDescription.init(stereoGlobalTapButExcludeProcesses: excludeProcesses)
} else if !includeProcesses.isEmpty {
    tapDesc = CATapDescription.init(stereoMixdownOfProcesses: includeProcesses)
}
```

#### Signal Handling

- Implemented SIGINT/SIGTERM handlers for graceful cleanup
- Ensures AudioHardwareDestroyProcessTap is called on exit

### 2. Python Backend Enhancements

**File:** `src/proctap/backends/macos.py`

#### New Parameters

```python
class MacOSBackend(AudioBackend):
    def __init__(
        self,
        pid: int,
        sample_rate: int = 48000,
        channels: int = 2,
        sample_width: int = 2,
        include_pids: Optional[list[int]] = None,  # NEW
        exclude_pids: Optional[list[int]] = None,  # NEW
        device: Optional[str] = None,              # NEW
    ) -> None:
```

#### Backward Compatibility

- `pid` parameter maintained for backward compatibility
- If `include_pids` is `None` and `pid > 0`, it's converted to `include_pids=[pid]`
- If both are `None` or `pid=0`, captures all processes

#### Command Building

```python
cmd = [str(self._helper_path), "--sample-rate", str(self._sample_rate), "--channels", str(self._channels)]

if self._include_pids:
    cmd.extend(["--include-pids", ",".join(map(str, self._include_pids))])

if self._exclude_pids:
    cmd.extend(["--exclude-pids", ",".join(map(str, self._exclude_pids))])

if self._device:
    cmd.extend(["--device", self._device])
```

### 3. Examples

#### Basic Example (Updated)

**File:** `examples/macos_basic.py`

- Demonstrates single process capture
- Backward compatible with existing API

#### Advanced Example (NEW)

**File:** `examples/macos_advanced.py`

- Demonstrates multi-process capture
- Shows include/exclude PIDs usage
- Supports process name resolution via psutil

**Usage Examples:**

```bash
# Capture from multiple specific processes
python macos_advanced.py --include-pids 1234,5678 --duration 5 --output multi.wav

# Capture all except music player
python macos_advanced.py --exclude-pids 9999 --duration 10 --output no_music.wav

# Capture game + voice chat, exclude music (by name)
python macos_advanced.py --include-names "game,discord" --exclude-names "Music" --duration 10
```

## Technical Details

### Type Conversion Fix

Fixed compilation errors related to `CATapDescription` initializers:

- **Problem**: Initial implementation used `[NSNumber]` arrays
- **Solution**: Changed to `[AudioObjectID]` (which is `[UInt32]`)
- **Reason**: `CATapDescription` initializers are marked with `NS_REFINED_FOR_SWIFT` and expect native Swift types

```swift
// Before (FAILED)
var includeObjects: [NSNumber] = []
includeObjects.append(NSNumber(value: obj))

// After (SUCCESS)
var includeObjects: [AudioObjectID] = []
includeObjects.append(obj)
```

### Availability Annotations

Fixed global variable availability issues:

```swift
// Before (FAILED)
@available(macOS 14.2, *)
var tapInstance: ProcessAudioTap?

// After (SUCCESS)
var tapInstance: Any?  // Type-erased to avoid availability annotation on global

// Usage in signal handlers
if #available(macOS 14.2, *) {
    (tapInstance as? ProcessAudioTap)?.stop()
}
```

## Build & Deployment

### Build Commands

```bash
# Build Swift CLI helper
cd swift/proctap-macos
swift build -c release

# Copy to package directory
cp .build/release/proctap-macos ../../src/proctap/bin/
```

### Build Output

- Binary size: ~111KB
- Build time: ~1.2s
- Platform: macOS arm64

### Build Warnings

Minor warning (safe to ignore):
```
warning: forming 'UnsafeMutableRawPointer' to a variable of type 'CFString'
```

This is a common pattern in Core Audio code and does not affect functionality.

## Testing

### Manual Testing Performed

1. ✅ Swift helper compiles without errors
2. ✅ Binary runs and shows correct help message
3. ✅ Python backend finds helper binary correctly
4. ✅ `MacOSBackend` initialization with include/exclude PIDs works
5. ✅ Command building logic produces correct arguments

### Testing Requirements

⚠️ **Note**: Full end-to-end testing requires:
- macOS 14.4+ (Sonoma) or later
- Processes actively playing audio
- Audio capture permission granted

**Test Scenarios:**

```bash
# Test single process capture
python examples/macos_basic.py --pid <PID> --duration 5 --output test.wav

# Test multi-process capture
python examples/macos_advanced.py --include-pids <PID1>,<PID2> --duration 5 --output multi.wav

# Test exclude mode
python examples/macos_advanced.py --exclude-pids <PID> --duration 5 --output exclude.wav

# Test by process name
python examples/macos_advanced.py --include-names "Safari,Music" --duration 10 --output named.wav
```

## Use Cases

### 1. Game + Voice Chat Capture

```python
backend = MacOSBackend(
    pid=0,
    include_pids=[game_pid, discord_pid],
    exclude_pids=[music_pid],
    sample_rate=48000,
    channels=2
)
```

Captures audio from game and Discord voice chat while excluding background music.

### 2. Exclude Music Player

```python
backend = MacOSBackend(
    pid=0,
    exclude_pids=[music_app_pid],
    sample_rate=16000,
    channels=1
)
```

Captures all system audio except music player (useful for voice recording).

### 3. Multiple App Capture

```python
backend = MacOSBackend(
    pid=0,
    include_pids=[safari_pid, chrome_pid, firefox_pid],
    sample_rate=44100,
    channels=2
)
```

Captures audio only from web browsers.

## Known Limitations

1. **Process Must Be Playing Audio**: Core Audio Process Tap only works when processes have active audio output streams
2. **macOS 14.4+ Required**: Process Tap API is only available on macOS 14.4 (Sonoma) or later
3. **Permission Required**: First run triggers macOS audio capture permission dialog
4. **Max PIDs**: While the API doesn't enforce a hard limit, performance may degrade with many PIDs

## Files Modified

### New Files

- `examples/macos_advanced.py` - Advanced usage example
- `docs/macos_include_exclude_pids_implementation.md` - This document

### Modified Files

- `swift/proctap-macos/Sources/main.swift` - Full rewrite with include/exclude support
- `src/proctap/backends/macos.py` - Added include_pids, exclude_pids, device parameters

### Binary Output

- `src/proctap/bin/proctap-macos` - Built Swift CLI helper (111KB)

## Compatibility

### Backward Compatibility

✅ **Fully backward compatible** with existing code:

```python
# Old code (still works)
backend = MacOSBackend(pid=1234, sample_rate=48000, channels=2)

# New code
backend = MacOSBackend(
    pid=0,
    include_pids=[1234, 5678],
    exclude_pids=[9999],
    sample_rate=48000,
    channels=2
)
```

### API Compatibility

- Old `pid` parameter preserved
- New parameters are optional (`None` by default)
- If both `pid` and `include_pids` are specified, `include_pids` takes precedence

## Future Improvements

1. **Dynamic PID Management**: Add/remove PIDs during capture
2. **PID Auto-Discovery**: Automatically find processes playing audio
3. **Process Name Support**: Built-in process name → PID resolution
4. **Format Negotiation**: Query tap device format and adapt automatically
5. **Error Recovery**: Reconnect if process restarts
6. **Metrics**: Track per-process audio levels and statistics

## References

1. [Core Audio Process Tap API - Apple Developer](https://developer.apple.com/documentation/coreaudio/1533210-audiohardwarecreateprocesstap)
2. [CATapDescription - Core Audio Header](https://github.com/phracker/MacOSX-SDKs/blob/master/MacOSX10.15.sdk/System/Library/Frameworks/CoreAudio.framework/Headers/AudioHardware.h)
3. [GitHub Issue #8 - PyObjC Backend Research](https://github.com/m96-chan/ProcTap/issues/8)

---

**Implementation Author:** Claude (AI Assistant)
**Implementation Date:** 2025-11-18
**Status:** ✅ Complete and ready for testing
