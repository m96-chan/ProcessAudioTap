/*
 * macOS Native Process Tap Extension
 *
 * Provides Python bindings for macOS Core Audio Process Tap API
 * using AudioDeviceCreateIOProcIDWithBlock for reliable callbacks.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <CoreAudio/CoreAudio.h>
#include <AudioToolbox/AudioToolbox.h>
#include <CoreFoundation/CoreFoundation.h>
#include <dispatch/dispatch.h>
#include <objc/runtime.h>
#include <objc/message.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Forward declarations for Core Audio private/undocumented APIs
extern OSStatus AudioHardwareCreateProcessTap(id tapDescription, AudioObjectID* outTapID);
extern OSStatus AudioHardwareDestroyProcessTap(AudioObjectID tapID);

// Custom property selector for process PID (not in public headers)
#define kAudioProcessObjectPropertyPID 'pid '

// Audio buffer queue for passing data to Python
#define MAX_QUEUE_SIZE 100

typedef struct {
    void* data;
    size_t size;
} AudioChunk;

typedef struct {
    AudioChunk chunks[MAX_QUEUE_SIZE];
    int read_pos;
    int write_pos;
    int count;
    pthread_mutex_t mutex;
} AudioQueue;

// ProcessTap object
typedef struct {
    PyObject_HEAD
    pid_t pid;
    AudioObjectID process_object_id;
    AudioObjectID tap_device_id;
    AudioObjectID aggregate_device_id;
    AudioDeviceIOProcID io_proc_id;
    AudioQueue* queue;
    dispatch_queue_t dispatch_queue;
    CFStringRef tap_uuid;
    int is_running;
    int sample_rate;
    int channels;
    int bits_per_sample;
} ProcessTapObject;

// Forward declarations
static PyTypeObject ProcessTapType;

// Audio queue functions
static AudioQueue* audio_queue_create(void) {
    AudioQueue* queue = (AudioQueue*)malloc(sizeof(AudioQueue));
    if (!queue) return NULL;

    memset(queue, 0, sizeof(AudioQueue));
    pthread_mutex_init(&queue->mutex, NULL);
    return queue;
}

static void audio_queue_destroy(AudioQueue* queue) {
    if (!queue) return;

    pthread_mutex_lock(&queue->mutex);

    // Free all chunks
    for (int i = 0; i < MAX_QUEUE_SIZE; i++) {
        if (queue->chunks[i].data) {
            free(queue->chunks[i].data);
            queue->chunks[i].data = NULL;
        }
    }

    pthread_mutex_unlock(&queue->mutex);
    pthread_mutex_destroy(&queue->mutex);
    free(queue);
}

static int audio_queue_push(AudioQueue* queue, const void* data, size_t size) {
    if (!queue || !data || size == 0) return 0;

    pthread_mutex_lock(&queue->mutex);

    if (queue->count >= MAX_QUEUE_SIZE) {
        pthread_mutex_unlock(&queue->mutex);
        return 0; // Queue full
    }

    // Allocate and copy data
    void* chunk_data = malloc(size);
    if (!chunk_data) {
        pthread_mutex_unlock(&queue->mutex);
        return 0;
    }

    memcpy(chunk_data, data, size);

    queue->chunks[queue->write_pos].data = chunk_data;
    queue->chunks[queue->write_pos].size = size;
    queue->write_pos = (queue->write_pos + 1) % MAX_QUEUE_SIZE;
    queue->count++;

    pthread_mutex_unlock(&queue->mutex);
    return 1;
}

static AudioChunk audio_queue_pop(AudioQueue* queue) {
    AudioChunk chunk = {NULL, 0};
    if (!queue) return chunk;

    pthread_mutex_lock(&queue->mutex);

    if (queue->count == 0) {
        pthread_mutex_unlock(&queue->mutex);
        return chunk;
    }

    chunk = queue->chunks[queue->read_pos];
    queue->chunks[queue->read_pos].data = NULL;
    queue->chunks[queue->read_pos].size = 0;
    queue->read_pos = (queue->read_pos + 1) % MAX_QUEUE_SIZE;
    queue->count--;

    pthread_mutex_unlock(&queue->mutex);
    return chunk;
}

// Find process audio object ID
static AudioObjectID find_process_object_id(pid_t pid) {
    AudioObjectPropertyAddress property_address = {
        .mSelector = kAudioHardwarePropertyProcessObjectList,
        .mScope = kAudioObjectPropertyScopeGlobal,
        .mElement = kAudioObjectPropertyElementMain
    };

    UInt32 data_size = 0;
    OSStatus status = AudioObjectGetPropertyDataSize(
        kAudioObjectSystemObject,
        &property_address,
        0, NULL,
        &data_size
    );

    fprintf(stderr, "DEBUG: Finding process object for PID %d\n", pid);
    fprintf(stderr, "DEBUG: AudioObjectGetPropertyDataSize status=%d, data_size=%u\n", status, data_size);

    if (status != noErr || data_size == 0) {
        fprintf(stderr, "DEBUG: Failed to get process object list size\n");
        return kAudioObjectUnknown;
    }

    int count = data_size / sizeof(AudioObjectID);
    AudioObjectID* process_objects = (AudioObjectID*)malloc(data_size);
    if (!process_objects) return kAudioObjectUnknown;

    status = AudioObjectGetPropertyData(
        kAudioObjectSystemObject,
        &property_address,
        0, NULL,
        &data_size,
        process_objects
    );

    if (status != noErr) {
        free(process_objects);
        return kAudioObjectUnknown;
    }

    // Find matching PID
    AudioObjectID result = kAudioObjectUnknown;
    AudioObjectPropertyAddress pid_property = {
        .mSelector = kAudioProcessObjectPropertyPID,  // Use our defined constant
        .mScope = kAudioObjectPropertyScopeGlobal,
        .mElement = kAudioObjectPropertyElementMain
    };

    fprintf(stderr, "DEBUG: Found %d process objects\n", count);

    for (int i = 0; i < count; i++) {
        pid_t process_pid = 0;
        UInt32 pid_size = sizeof(pid_t);

        status = AudioObjectGetPropertyData(
            process_objects[i],
            &pid_property,
            0, NULL,
            &pid_size,
            &process_pid
        );

        fprintf(stderr, "DEBUG: Process object %d: status=%d, pid=%d (looking for %d)\n", process_objects[i], status, process_pid, pid);

        if (status == noErr && process_pid == pid) {
            fprintf(stderr, "DEBUG: MATCH FOUND! Object ID: %d\n", process_objects[i]);
            result = process_objects[i];
            break;
        }
    }

    free(process_objects);
    fprintf(stderr, "DEBUG: Returning object ID: %d\n", result);
    return result;
}

// Create Process Tap
static OSStatus create_process_tap(AudioObjectID process_object_id, AudioObjectID* tap_device_id, CFStringRef* uuid_out) {
    // Get CATapDescription class
    Class CATapDescriptionClass = objc_getClass("CATapDescription");
    if (!CATapDescriptionClass) {
        fprintf(stderr, "CATapDescription class not found\n");
        return -1;
    }

    // Create NSArray with process object ID
    id (*msgSend_uint)(id, SEL, unsigned int) = (id (*)(id, SEL, unsigned int))objc_msgSend;
    id (*msgSend_id)(id, SEL, id) = (id (*)(id, SEL, id))objc_msgSend;
    id (*msgSend_alloc)(Class, SEL) = (id (*)(Class, SEL))objc_msgSend;

    id number = msgSend_uint(objc_getClass("NSNumber"), sel_registerName("numberWithUnsignedInt:"), process_object_id);
    id array = msgSend_id(objc_getClass("NSArray"), sel_registerName("arrayWithObject:"), number);

    // Create CATapDescription
    id tap_desc = msgSend_alloc(CATapDescriptionClass, sel_registerName("alloc"));
    tap_desc = msgSend_id(tap_desc, sel_registerName("initStereoMixdownOfProcesses:"), array);

    // Create UUID
    CFUUIDRef uuid = CFUUIDCreate(NULL);
    CFStringRef uuid_string = CFUUIDCreateString(NULL, uuid);
    CFRelease(uuid);

    // Set UUID on tap description
    Class nsuuid_class = objc_getClass("NSUUID");
    id nsuuid = msgSend_alloc(nsuuid_class, sel_registerName("alloc"));
    nsuuid = msgSend_id(nsuuid, sel_registerName("initWithUUIDString:"), uuid_string);
    msgSend_id(tap_desc, sel_registerName("setUUID:"), nsuuid);

    // Create Process Tap
    OSStatus status = AudioHardwareCreateProcessTap(tap_desc, tap_device_id);

    if (status == noErr) {
        *uuid_out = uuid_string;
    } else {
        CFRelease(uuid_string);
    }

    return status;
}

// Create Aggregate Device
static OSStatus create_aggregate_device(AudioObjectID tap_device_id, CFStringRef tap_uuid, AudioObjectID* aggregate_device_id) {
    // Get default output device UID
    AudioObjectPropertyAddress property = {
        .mSelector = kAudioHardwarePropertyDefaultOutputDevice,
        .mScope = kAudioObjectPropertyScopeGlobal,
        .mElement = kAudioObjectPropertyElementMain
    };

    AudioObjectID output_device_id = kAudioObjectUnknown;
    UInt32 size = sizeof(AudioObjectID);
    OSStatus status = AudioObjectGetPropertyData(
        kAudioObjectSystemObject,
        &property,
        0, NULL,
        &size,
        &output_device_id
    );

    CFStringRef output_uid = NULL;
    if (status == noErr) {
        AudioObjectPropertyAddress uid_property = {
            .mSelector = kAudioDevicePropertyDeviceUID,
            .mScope = kAudioObjectPropertyScopeGlobal,
            .mElement = kAudioObjectPropertyElementMain
        };

        size = sizeof(CFStringRef);
        AudioObjectGetPropertyData(
            output_device_id,
            &uid_property,
            0, NULL,
            &size,
            &output_uid
        );
    }

    if (!output_uid) {
        output_uid = CFStringCreateWithCString(NULL, "BuiltInSpeakerDevice", kCFStringEncodingUTF8);
    }

    // Create aggregate device UUID
    CFUUIDRef agg_uuid = CFUUIDCreate(NULL);
    CFStringRef agg_uuid_string = CFUUIDCreateString(NULL, agg_uuid);
    CFRelease(agg_uuid);

    // Build aggregate device description
    CFMutableDictionaryRef description = CFDictionaryCreateMutable(
        NULL, 0,
        &kCFTypeDictionaryKeyCallBacks,
        &kCFTypeDictionaryValueCallBacks
    );

    CFStringRef name = CFStringCreateWithCString(NULL, "ProcTap Aggregate", kCFStringEncodingUTF8);
    CFDictionarySetValue(description, CFSTR("name"), name);
    CFDictionarySetValue(description, CFSTR("uid"), agg_uuid_string);
    CFDictionarySetValue(description, CFSTR("private"), kCFBooleanTrue);
    CFDictionarySetValue(description, CFSTR("stacked"), kCFBooleanFalse);
    CFDictionarySetValue(description, CFSTR("autostart"), kCFBooleanTrue);
    CFDictionarySetValue(description, CFSTR("master"), output_uid);

    // Sub-device list
    CFMutableDictionaryRef sub_device = CFDictionaryCreateMutable(NULL, 0, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    CFDictionarySetValue(sub_device, CFSTR("uid"), output_uid);

    CFArrayRef sub_device_list = CFArrayCreate(NULL, (const void**)&sub_device, 1, &kCFTypeArrayCallBacks);
    CFDictionarySetValue(description, CFSTR("subdevices"), sub_device_list);

    // Tap list
    CFMutableDictionaryRef tap_dict = CFDictionaryCreateMutable(NULL, 0, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    CFDictionarySetValue(tap_dict, CFSTR("drift"), kCFBooleanTrue);
    CFDictionarySetValue(tap_dict, CFSTR("uid"), tap_uuid);

    CFArrayRef tap_list = CFArrayCreate(NULL, (const void**)&tap_dict, 1, &kCFTypeArrayCallBacks);
    CFDictionarySetValue(description, CFSTR("taps"), tap_list);

    // Create aggregate device
    status = AudioHardwareCreateAggregateDevice(description, aggregate_device_id);

    // Cleanup
    CFRelease(tap_list);
    CFRelease(tap_dict);
    CFRelease(sub_device_list);
    CFRelease(sub_device);
    CFRelease(description);
    CFRelease(name);
    CFRelease(agg_uuid_string);
    CFRelease(output_uid);

    return status;
}

// ProcessTap.__init__
static int ProcessTap_init(ProcessTapObject* self, PyObject* args, PyObject* kwargs) {
    static char* kwlist[] = {"pid", "sample_rate", "channels", "bits_per_sample", NULL};

    self->pid = 0;
    self->sample_rate = 48000;
    self->channels = 2;
    self->bits_per_sample = 16;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "i|iii", kwlist,
                                      &self->pid, &self->sample_rate,
                                      &self->channels, &self->bits_per_sample)) {
        return -1;
    }

    self->process_object_id = kAudioObjectUnknown;
    self->tap_device_id = kAudioObjectUnknown;
    self->aggregate_device_id = kAudioObjectUnknown;
    self->io_proc_id = NULL;
    self->queue = audio_queue_create();
    self->dispatch_queue = NULL;
    self->tap_uuid = NULL;
    self->is_running = 0;

    if (!self->queue) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to create audio queue");
        return -1;
    }

    return 0;
}

// ProcessTap.__dealloc__
static void ProcessTap_dealloc(ProcessTapObject* self) {
    // Stop if running
    if (self->is_running) {
        if (self->io_proc_id && self->aggregate_device_id != kAudioObjectUnknown) {
            AudioDeviceStop(self->aggregate_device_id, self->io_proc_id);
            AudioDeviceDestroyIOProcID(self->aggregate_device_id, self->io_proc_id);
        }

        if (self->aggregate_device_id != kAudioObjectUnknown) {
            AudioHardwareDestroyAggregateDevice(self->aggregate_device_id);
        }

        if (self->tap_device_id != kAudioObjectUnknown) {
            AudioHardwareDestroyProcessTap(self->tap_device_id);
        }
    }

    if (self->queue) {
        audio_queue_destroy(self->queue);
    }

    if (self->dispatch_queue) {
        dispatch_release(self->dispatch_queue);
    }

    if (self->tap_uuid) {
        CFRelease(self->tap_uuid);
    }

    Py_TYPE(self)->tp_free((PyObject*)self);
}

// ProcessTap.start()
static PyObject* ProcessTap_start(ProcessTapObject* self, PyObject* Py_UNUSED(ignored)) {
    if (self->is_running) {
        PyErr_SetString(PyExc_RuntimeError, "Already running");
        return NULL;
    }

    // Step 1: Find process audio object
    self->process_object_id = find_process_object_id(self->pid);
    if (self->process_object_id == kAudioObjectUnknown) {
        PyErr_Format(PyExc_RuntimeError, "Process %d has no audio", self->pid);
        return NULL;
    }

    // Step 2: Create Process Tap
    OSStatus status = create_process_tap(self->process_object_id, &self->tap_device_id, &self->tap_uuid);
    if (status != noErr) {
        PyErr_Format(PyExc_RuntimeError, "Failed to create Process Tap: status=%d", status);
        return NULL;
    }

    // Step 3: Create Aggregate Device
    status = create_aggregate_device(self->tap_device_id, self->tap_uuid, &self->aggregate_device_id);
    if (status != noErr) {
        AudioHardwareDestroyProcessTap(self->tap_device_id);
        PyErr_Format(PyExc_RuntimeError, "Failed to create Aggregate Device: status=%d", status);
        return NULL;
    }

    // Step 4: Create dispatch queue
    self->dispatch_queue = dispatch_queue_create("com.proctap.ioproc", DISPATCH_QUEUE_SERIAL);
    if (!self->dispatch_queue) {
        AudioHardwareDestroyAggregateDevice(self->aggregate_device_id);
        AudioHardwareDestroyProcessTap(self->tap_device_id);
        PyErr_SetString(PyExc_RuntimeError, "Failed to create dispatch queue");
        return NULL;
    }

    // Step 5: Create IOProc with block
    AudioQueue* queue = self->queue; // Capture for block

    status = AudioDeviceCreateIOProcIDWithBlock(
        &self->io_proc_id,
        self->aggregate_device_id,
        self->dispatch_queue,
        ^(const AudioTimeStamp* inNow,
          const AudioBufferList* inInputData,
          const AudioTimeStamp* inInputTime,
          AudioBufferList* outOutputData,
          const AudioTimeStamp* inOutputTime) {
            // IOProc block callback
            if (inInputData && inInputData->mNumberBuffers > 0) {
                const AudioBuffer* buffer = &inInputData->mBuffers[0];
                if (buffer->mData && buffer->mDataByteSize > 0) {
                    audio_queue_push(queue, buffer->mData, buffer->mDataByteSize);
                }
            }
        }
    );

    if (status != noErr) {
        dispatch_release(self->dispatch_queue);
        AudioHardwareDestroyAggregateDevice(self->aggregate_device_id);
        AudioHardwareDestroyProcessTap(self->tap_device_id);
        PyErr_Format(PyExc_RuntimeError, "Failed to create IOProc: status=%d", status);
        return NULL;
    }

    // Step 6: Start device
    status = AudioDeviceStart(self->aggregate_device_id, self->io_proc_id);
    if (status != noErr) {
        AudioDeviceDestroyIOProcID(self->aggregate_device_id, self->io_proc_id);
        dispatch_release(self->dispatch_queue);
        AudioHardwareDestroyAggregateDevice(self->aggregate_device_id);
        AudioHardwareDestroyProcessTap(self->tap_device_id);
        PyErr_Format(PyExc_RuntimeError, "Failed to start device: status=%d", status);
        return NULL;
    }

    self->is_running = 1;
    Py_RETURN_NONE;
}

// ProcessTap.stop()
static PyObject* ProcessTap_stop(ProcessTapObject* self, PyObject* Py_UNUSED(ignored)) {
    if (!self->is_running) {
        Py_RETURN_NONE;
    }

    if (self->io_proc_id && self->aggregate_device_id != kAudioObjectUnknown) {
        AudioDeviceStop(self->aggregate_device_id, self->io_proc_id);
        AudioDeviceDestroyIOProcID(self->aggregate_device_id, self->io_proc_id);
        self->io_proc_id = NULL;
    }

    if (self->aggregate_device_id != kAudioObjectUnknown) {
        AudioHardwareDestroyAggregateDevice(self->aggregate_device_id);
        self->aggregate_device_id = kAudioObjectUnknown;
    }

    if (self->tap_device_id != kAudioObjectUnknown) {
        AudioHardwareDestroyProcessTap(self->tap_device_id);
        self->tap_device_id = kAudioObjectUnknown;
    }

    if (self->dispatch_queue) {
        dispatch_release(self->dispatch_queue);
        self->dispatch_queue = NULL;
    }

    self->is_running = 0;
    Py_RETURN_NONE;
}

// ProcessTap.read()
static PyObject* ProcessTap_read(ProcessTapObject* self, PyObject* Py_UNUSED(ignored)) {
    if (!self->is_running) {
        Py_RETURN_NONE;
    }

    AudioChunk chunk = audio_queue_pop(self->queue);
    if (!chunk.data) {
        Py_RETURN_NONE;
    }

    PyObject* result = PyBytes_FromStringAndSize((const char*)chunk.data, chunk.size);
    free(chunk.data);

    return result;
}

// Method definitions
static PyMethodDef ProcessTap_methods[] = {
    {"start", (PyCFunction)ProcessTap_start, METH_NOARGS, "Start audio capture"},
    {"stop", (PyCFunction)ProcessTap_stop, METH_NOARGS, "Stop audio capture"},
    {"read", (PyCFunction)ProcessTap_read, METH_NOARGS, "Read audio chunk"},
    {NULL}
};

// Type definition
static PyTypeObject ProcessTapType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_macos_native.ProcessTap",
    .tp_doc = "Native macOS Process Tap",
    .tp_basicsize = sizeof(ProcessTapObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = PyType_GenericNew,
    .tp_init = (initproc)ProcessTap_init,
    .tp_dealloc = (destructor)ProcessTap_dealloc,
    .tp_methods = ProcessTap_methods,
};

// Module definition
static PyModuleDef macos_native_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_macos_native",
    .m_doc = "Native macOS Process Tap extension",
    .m_size = -1,
};

// Module initialization
PyMODINIT_FUNC PyInit__macos_native(void) {
    PyObject* m;

    if (PyType_Ready(&ProcessTapType) < 0) {
        return NULL;
    }

    m = PyModule_Create(&macos_native_module);
    if (m == NULL) {
        return NULL;
    }

    Py_INCREF(&ProcessTapType);
    if (PyModule_AddObject(m, "ProcessTap", (PyObject*)&ProcessTapType) < 0) {
        Py_DECREF(&ProcessTapType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}
