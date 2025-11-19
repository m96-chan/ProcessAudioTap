# TCC Permission Implementation - Complete

## Summary

Successfully implemented automatic TCC (Transparency, Consent, and Control) microphone permission handling for the macOS PyObjC backend. The implementation follows the AudioCap architecture and includes Priority 1 & 2 critical fixes.

## What Was Implemented

### 1. Core Audio ctypes Bindings (`macos_coreaudio_ctypes.py`)

#### AudioObjectGetPropertyData Implementation
- Direct ctypes binding to Core Audio property query API
- Properly handles all Core Audio property types (uint32, CFString, AudioStreamBasicDescription)
- Replaces problematic PyObjC "converting to a C array" errors

#### Priority 1: Tap Stream Format Reading (CRITICAL - AudioCap line 133)
```python
def read_tap_stream_format(tap_device_id: int) -> tuple[bool, dict]:
    """
    Read AudioStreamBasicDescription (40 bytes) from tap device.

    This is CRITICAL per AudioCap implementation - must be done BEFORE
    creating the aggregate device.
    """
```

**Why Critical**: AudioCap marks this as CRITICAL because reading the tap stream format "activates" the tap device and ensures proper initialization before aggregate device creation.

#### Priority 2: Default Output Device UID
```python
def get_default_output_device_uid() -> tuple[bool, str]:
    """
    Get actual system default output device UID.

    Replaces hardcoded fallback "BuiltInSpeakerDevice" with real device UID.
    Essential for proper aggregate device configuration.
    """
```

**Why Important**: The aggregate device needs the correct system output device UID as its main sub-device. Using a fallback value breaks the audio routing.

### 2. TCC Permission Management

#### Permission Checking
```python
def check_audio_capture_permission() -> tuple[bool, str]:
    """
    Check if audio capture permission is granted by attempting to read
    tap stream format property. Status 2003332927 ('wat?') = denied.
    """
```

#### Automatic Permission Request
```python
def request_microphone_permission() -> bool:
    """
    Triggers macOS system permission dialog using AVFoundation.

    Uses osascript with JavaScript to call:
    AVCaptureDevice.defaultDeviceWithMediaType(AVMediaTypeAudio)

    This causes macOS to show the permission dialog if not already granted.
    """
```

#### System Settings Auto-Open
```python
def open_system_preferences_privacy():
    """
    Opens System Settings → Privacy & Security → Microphone.

    URL: x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone
    """
```

#### User-Friendly Help
```python
def print_tcc_help(auto_open: bool = True):
    """
    Prints clear, emoji-decorated instructions for granting permission.
    Optionally auto-opens System Settings.
    """
```

#### Main Entry Point
```python
def ensure_microphone_permission(
    auto_request: bool = True,
    auto_open_settings: bool = True
) -> bool:
    """
    Main function - orchestrates the entire permission flow:
    1. Check if already granted → return True
    2. Try to trigger system dialog → return True if granted
    3. Show help and open System Settings → return False
    """
```

### 3. Integration with MacOSNativeBackend

Modified `MacOSNativeBackend.__init__()` (lines 395-410):
```python
# Check and request TCC permissions (with ctypes if available)
if CTYPES_AVAILABLE:
    if not ca_ctypes.ensure_microphone_permission(
        auto_request=True,
        auto_open_settings=True
    ):
        logger.error("Microphone permission is required but not granted")
        raise RuntimeError(
            "Microphone permission denied. "
            "Please grant permission in System Settings → Privacy & Security → Microphone, "
            "then restart this application."
        )
```

## Architecture Achieved

```
AudioCap Flow (Swift)          ProcTap Flow (Python/ctypes)
─────────────────────         ─────────────────────────────
1. Process Tap                 ✅ AudioHardwareCreateProcessTap (PyObjC)
2. Read tap format ⚠️         ✅ read_tap_stream_format (ctypes) - Priority 1
3. Get output device UID       ✅ get_default_output_device_uid (ctypes) - Priority 2
4. Create Aggregate            ✅ AudioHardwareCreateAggregateDevice (ctypes)
5. Attach IOProc               ✅ AudioDeviceCreateIOProcID (PyObjC)
6. Start device                ✅ AudioDeviceStart (ctypes)
7. Request TCC permission      ✅ ensure_microphone_permission (ctypes)
8. Capture audio               ⏳ Ready for testing with granted permission
```

## Testing Instructions

### Prerequisites
1. macOS 14.4 (Sonoma) or later
2. PyObjC installed: `pip install pyobjc-core pyobjc-framework-CoreAudio`
3. A process that plays audio (e.g., Music.app, Safari with video, `say` command)

### Test Steps

#### Option 1: Using the Test Script
```bash
# Start an audio process (in a separate terminal)
say "This is a test of the audio capture system. Testing one two three." &

# Get the PID
pgrep -fl say

# Run the test (replace 12345 with actual PID)
python3.12 examples/macos_pyobjc_capture_test.py --pid 12345 --duration 5 --output test.wav
```

#### Option 2: Using a Named Process
```bash
# Capture from Music.app (make sure it's playing something)
python3.12 examples/macos_pyobjc_capture_test.py --name Music --duration 5 --output music.wav

# Capture from Safari
python3.12 examples/macos_pyobjc_capture_test.py --name Safari --duration 10 --output safari.wav
```

### Expected Behavior

#### First Run (No Permission Granted Yet)
1. **Permission Dialog Appears**: A macOS system dialog will appear asking:
   ```
   "Terminal" would like to access the microphone.
   [Don't Allow] [OK]
   ```

2. **Click "OK"** to grant permission

3. **If You Click "Don't Allow"**:
   - The script will automatically open System Settings
   - Navigate to: Privacy & Security → Microphone
   - Enable the checkbox next to "Terminal" (or "Python")
   - Restart the script

#### After Permission Granted
```
macOS Version: 14.4.0
PyObjC Status: Available ✓
Process Tap API: Supported ✓

Testing PyObjC audio capture for PID 12345
Configuration: 48000Hz, 2ch, 16bit
Duration: 5.0 seconds
============================================================
Creating MacOSNativeBackend...
✅ Microphone permission already granted

Starting audio capture...
Creating process tap for PID 12345...
✓ Process tap created: device ID 117

Reading tap stream format (CRITICAL)...
✓ Tap format: 48000 Hz, 2 channels, 32-bit float PCM

Getting default output device UID...
✓ Default output device UID: AppleHDAEngineOutput:1B,0,1,0:0

Creating aggregate device...
✓ Aggregate device created: ID 118

Starting aggregate device...
✓ Device started successfully

Capturing audio for 5.0 seconds...
  [5.0s] Captured 500 chunks, 960,000 bytes

Stopping audio capture...
============================================================
Capture Results:
  Total chunks: 500
  Total bytes: 960,000
  Actual duration: 5.00 seconds

Phase 2 Test: PASSED ✓

Saved 500 chunks to test.wav
Total size: 960,000 bytes
Duration: 5.00 seconds
```

## Technical Details

### Error Status Codes
- `0` = Success
- `2003332927` (0x7761743F) = 'wat?' = TCC microphone permission denied
- `560947818` (0x216e6f21) = '!no!' = Property not found or device doesn't exist

### Critical Implementation Notes

1. **Tap Stream Format Reading is CRITICAL**
   - AudioCap marks this as CRITICAL (line 133)
   - Must be done BEFORE aggregate device creation
   - Activates/initializes the tap device
   - Without this, IOProc callback will not receive data

2. **TCC Permission is Process-Level**
   - Each terminal/IDE needs separate permission grant
   - Terminal.app vs iTerm2 vs VS Code are different
   - Python interpreter vs `python3.12` vs virtualenv are different

3. **Audio Must Be Playing**
   - Process tap only captures audio currently being played
   - If process is silent, 0 bytes will be captured
   - This is expected behavior, not a bug

4. **Aggregate Device Cleanup**
   - Aggregate devices are automatically destroyed on stop
   - Device IDs are reused (117, 118, etc.)

## Problem Solving Summary

### Problem 1: PyObjC Segmentation Faults
**Error**: `AudioHardwareCreateAggregateDevice` caused segfault (exit 139)

**Solution**: Implemented direct ctypes bindings for problematic functions
- `AudioHardwareCreateAggregateDevice`
- `AudioHardwareDestroyAggregateDevice`
- `AudioDeviceStart`
- `AudioDeviceStop`

### Problem 2: IOProc Callback Not Called (0 bytes captured)
**Error**: Device started successfully but no audio data received

**Root Causes**:
1. Tap stream format not read (PyObjC "converting to a C array" error)
2. Default output device UID using hardcoded fallback

**Solution**:
- Implemented `AudioObjectGetPropertyData` with ctypes
- Implemented `read_tap_stream_format()` (Priority 1)
- Implemented `get_default_output_device_uid()` (Priority 2)

### Problem 3: TCC Permission Denied (status=2003332927)
**Error**: All Core Audio operations failing with 'wat?' status

**Root Cause**: Microphone permission not granted despite user's claim

**Solution**:
- Implemented `check_audio_capture_permission()` to detect denial
- Implemented `request_microphone_permission()` to trigger system dialog
- Implemented `open_system_preferences_privacy()` to guide user
- Integrated into backend initialization with clear error messages

## Files Modified/Created

### Created
- `/Users/djsaxia/projects/m96-chan/ProcTap/src/proctap/backends/macos_coreaudio_ctypes.py` (890 lines)
  - Complete ctypes bindings for Core Audio
  - Priority 1 & 2 fixes
  - TCC permission management

### Modified
- `/Users/djsaxia/projects/m96-chan/ProcTap/src/proctap/backends/macos_pyobjc.py`
  - Integrated ctypes functions for critical operations
  - Added TCC permission check on initialization
  - Replaced PyObjC calls with ctypes where needed

### Documentation
- `/Users/djsaxia/projects/m96-chan/ProcTap/debug_ioproc_issue.md` - Detailed problem analysis
- `/Users/djsaxia/projects/m96-chan/ProcTap/TCC_IMPLEMENTATION.md` - This file

## Next Steps

### For User Testing
1. Run the test script with an audio-playing process
2. Grant microphone permission when prompted
3. Verify audio capture works (bytes > 0)
4. Check that WAV file plays back correctly

### For Production
1. Add retry logic for transient Core Audio errors
2. Add audio level detection (silence vs actual audio)
3. Add buffer overflow detection
4. Consider adding permission pre-check before process discovery

### For Documentation
1. Update main README.md with TCC requirements
2. Add troubleshooting guide for common permission issues
3. Add screenshots of permission dialogs

## References

- **AudioCap (Swift)**: Reference implementation that this follows
  - Line 133: CRITICAL tap stream format read
  - Lines 140-165: Aggregate device configuration
- **Core Audio Documentation**: Apple's Core Audio framework
- **TCC Database**: `/Users/djsaxia/Library/Application Support/com.apple.TCC/TCC.db`

## Status: ✅ COMPLETE

All requested features implemented:
- ✅ Priority 1: Tap stream format reading (ctypes)
- ✅ Priority 2: Default output device UID (ctypes)
- ✅ TCC permission checking
- ✅ Automatic permission request dialog
- ✅ Auto-open System Settings
- ✅ User-friendly error messages and instructions
- ✅ Integration with MacOSNativeBackend

**Ready for user testing with granted TCC permissions.**
