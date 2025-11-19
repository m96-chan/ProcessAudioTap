# macOS C Extension Fix Summary

## Problem Found
`tapID=0` の原因: CATapDescription に PID を渡していたが、**AudioObjectID を期待していた**

## Solution
1. `kAudioHardwarePropertyTranslatePIDToProcessObject` 定数を追加
2. `translate_pid_to_process_object()` 関数を復元  
3. `create_process_tap()` で PID → AudioObjectID 変換を実行

## Code Changes Required

### 1. Add constant (after line 52):
```c
// Property selectors
#define kAudioHardwarePropertyTranslatePIDToProcessObject 0x70696432  // 'pid2'
```

### 2. Add function (after get_default_output_device_uid):
```c
/**
 * Translate PID to Process Object ID
 */
static OSStatus translate_pid_to_process_object(pid_t pid, AudioObjectID* out_object_id) {
    AudioObjectPropertyAddress address = {
        .mSelector = kAudioHardwarePropertyTranslatePIDToProcessObject,
        .mScope = kAudioObjectPropertyScopeGlobal,
        .mElement = kAudioObjectPropertyElementMain
    };

    UInt32 translation_value = (UInt32)pid;
    AudioObjectID process_object_id = 0;
    UInt32 data_size = sizeof(AudioObjectID);

    OSStatus status = AudioObjectGetPropertyData(
        kAudioObjectSystemObject,
        &address,
        sizeof(translation_value),
        &translation_value,
        &data_size,
        &process_object_id
    );

    if (status == noErr && out_object_id) {
        *out_object_id = process_object_id;
    }

    return status;
}
```

### 3. Modify create_process_tap (add PID → AudioObjectID conversion):
Before CATapDescription creation, add:
```c
// Convert PIDs to AudioObjectIDs
AudioObjectID* include_objects = NULL;
AudioObjectID* exclude_objects = NULL;

if (state->include_count > 0) {
    include_objects = (AudioObjectID*)malloc(sizeof(AudioObjectID) * state->include_count);
    for (size_t i = 0; i < state->include_count; i++) {
        OSStatus status = translate_pid_to_process_object(state->include_pids[i], &include_objects[i]);
        if (status != noErr) {
            snprintf(state->error_message, sizeof(state->error_message),
                    "Failed to translate PID %d to AudioObjectID", state->include_pids[i]);
            free(include_objects);
            return status;
        }
        NSLog(@"[DEBUG] PID %d → AudioObjectID %u", state->include_pids[i], include_objects[i]);
    }
}

// Similar for exclude_pids...
```

Then use `include_objects[i]` instead of `state->include_pids[i]` in NSArray creation.

Don't forget to free `include_objects` and `exclude_objects` before returning!
