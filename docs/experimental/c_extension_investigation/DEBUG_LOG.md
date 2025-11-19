# ProcTap macOS C Extension Debug Log

## Test Execution: 2025-11-18 04:33:13

### Process Information
- Target PID: 22578 (say command)
- Command: "This is a longer test message to ensure audio is playing during capture"

### Phase 1: Process Tap Creation ✅
```
[DEBUG] create_process_tap: Starting...
[DEBUG] create_process_tap: Creating CATapDescription...
[DEBUG] create_process_tap: Got tap UUID from description: 7B42E589-8E83-4365-B7EE-9C6D2DC1BE85
[DEBUG] create_process_tap: Calling AudioHardwareCreateProcessTap...
[DEBUG] create_process_tap: Process tap created with ID: 118 ✅
```
**Status**: SUCCESS - Valid tap ID (not 0)

### Phase 2: Default Device Detection ✅
```
[DEBUG] Getting default output device UID...
[DEBUG] Got device UID: BuiltInSpeakerDevice
```
**Status**: SUCCESS

### Phase 3: Aggregate Device Configuration ✅
```
[DEBUG] create_process_tap: Creating aggregate device...
[DEBUG] Generating aggregate UUID...
[DEBUG] Aggregate UUID: FF3B4E41-05A4-4023-9508-AC02E604D9D3
```

#### Sub-device Dictionary:
```json
{
    "uid": "BuiltInSpeakerDevice"
}
```

#### Tap Dictionary:
```json
{
    "drift": 1,
    "uid": "7B42E589-8E83-4365-B7EE-9C6D2DC1BE85"
}
```

#### Main Device Dictionary:
```json
{
    "TapAutoStart": 1,
    "TapList": [
        {
            "drift": 1,
            "uid": "7B42E589-8E83-4365-B7EE-9C6D2DC1BE85"
        }
    ],
    "master": "BuiltInSpeakerDevice",
    "name": "ProcTap Aggregate",
    "private": 1,
    "stacked": 0,
    "subdevices": [
        {
            "uid": "BuiltInSpeakerDevice"
        }
    ],
    "uid": "FF3B4E41-05A4-4023-9508-AC02E604D9D3"
}
```

### Phase 4: Aggregate Device Creation ✅
```
[DEBUG] Calling AudioHardwareCreateAggregateDevice...
[DEBUG] create_process_tap: AudioHardwareCreateAggregateDevice returned: 0, device_id: 119
```
**Status**: SUCCESS - OSStatus = 0 (noErr), Device ID = 119

### Phase 5: Device Initialization ✅
```
Wait time: 500ms
[DEBUG] create_process_tap: Aggregate device created successfully!
```

### Phase 6: IOProc Setup ✅
```
[DEBUG] IOProcID created for aggregate device 119
[DEBUG] Aggregate device started successfully!
```
**Status**: SUCCESS - AudioDeviceStart returned noErr

### Phase 7: Audio Capture ❌
```
Read 0 bytes
Read 0 bytes
Read 0 bytes
Read 0 bytes
Read 0 bytes
```
**Status**: FAILURE - No audio data received

**Possible Causes:**
1. IOProc callback not being invoked by CoreAudio
2. Input stream not configured on aggregate device
3. Stream format mismatch between tap and callback
4. Process Tap not producing data (process audio output issue)

### Phase 8: Cleanup ✅
```
[DEBUG] Aggregate device stopped
[DEBUG] Aggregate device destroyed
[DEBUG] Process tap destroyed
```
**Status**: SUCCESS

---

## Summary

### Working Components ✅
- [x] Process Tap creation (tap ID: 118)
- [x] UUID retrieval via KVC
- [x] Aggregate Device creation (device ID: 119)
- [x] IOProcID registration
- [x] Device start/stop lifecycle
- [x] Resource cleanup

### Not Working ❌
- [ ] Audio data flow through IOProc callback
- [ ] Ring buffer receiving data

### Comparison: Swift CLI vs C Extension

| Feature | Swift CLI | C Extension |
|---------|-----------|-------------|
| Process Tap | ❌ tapID=0 (global mode) | ✅ tapID=118 (PID mode) |
| Aggregate Device | N/A | ✅ device_id=119 |
| IOProc | N/A | ✅ Registered |
| Data Capture | ❌ Failed early | ❌ 0 bytes |

**Key Finding**: C extension successfully creates all devices but IOProc receives no data.

---

## Next Steps

1. **Add IOProc Callback Logging**
   - Verify if callback is being invoked
   - Check `inInputData` buffer status
   - Log buffer sizes and format

2. **Configure Input Stream Format**
   - Set `kAudioDevicePropertyStreamFormat` on input scope
   - Match format: 16kHz, 1ch, 16-bit PCM

3. **Verify Tap Data Flow**
   - Check if Process Tap is producing audio
   - Query tap device properties
   - Test with different audio sources

4. **Compare with Swift Implementation**
   - Review Swift's `configureDeviceFormat()`
   - Check for missing setup steps
