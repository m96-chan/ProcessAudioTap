"""
Direct Core Audio API bindings using ctypes.

This module provides low-level ctypes bindings to Core Audio APIs that
are not properly wrapped by PyObjC, specifically for Aggregate Device creation.

Based on Core Audio headers:
- AudioHardware.h
- AudioServerPlugIn.h
"""

import ctypes
import ctypes.util
import struct
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Load Core Audio framework
_core_audio = None
_core_foundation = None

def _load_frameworks():
    """Load Core Audio and Core Foundation frameworks."""
    global _core_audio, _core_foundation

    if _core_audio is None:
        framework_path = ctypes.util.find_library('CoreAudio')
        if not framework_path:
            raise RuntimeError("CoreAudio framework not found")
        _core_audio = ctypes.CDLL(framework_path)
        logger.debug(f"Loaded CoreAudio framework: {framework_path}")

    if _core_foundation is None:
        cf_path = ctypes.util.find_library('CoreFoundation')
        if not cf_path:
            raise RuntimeError("CoreFoundation framework not found")
        _core_foundation = ctypes.CDLL(cf_path)
        logger.debug(f"Loaded CoreFoundation framework: {cf_path}")

    return _core_audio, _core_foundation


# Core Audio types
AudioObjectID = ctypes.c_uint32
OSStatus = ctypes.c_int32
Boolean = ctypes.c_bool

# Core Foundation opaque types
CFTypeRef = ctypes.c_void_p
CFDictionaryRef = CFTypeRef
CFStringRef = CFTypeRef
CFArrayRef = CFTypeRef
CFNumberRef = CFTypeRef
CFBooleanRef = CFTypeRef


# Core Foundation functions
def CFStringCreateWithCString(allocator, cstr: bytes, encoding: int) -> CFStringRef:
    """Create CFString from C string."""
    cf_lib, _ = _load_frameworks()
    func = _core_foundation.CFStringCreateWithCString
    func.argtypes = [CFTypeRef, ctypes.c_char_p, ctypes.c_uint32]
    func.restype = CFStringRef
    return func(allocator, cstr, encoding)


def CFDictionaryCreate(
    allocator,
    keys: ctypes.POINTER(CFTypeRef),
    values: ctypes.POINTER(CFTypeRef),
    num_values: int,
    key_callbacks,
    value_callbacks
) -> CFDictionaryRef:
    """Create CFDictionary from keys and values."""
    func = _core_foundation.CFDictionaryCreate
    func.argtypes = [
        CFTypeRef,  # allocator
        ctypes.POINTER(CFTypeRef),  # keys
        ctypes.POINTER(CFTypeRef),  # values
        ctypes.c_long,  # numValues
        CFTypeRef,  # keyCallBacks
        CFTypeRef,  # valueCallBacks
    ]
    func.restype = CFDictionaryRef
    return func(allocator, keys, values, num_values, key_callbacks, value_callbacks)


def CFArrayCreate(
    allocator,
    values: ctypes.POINTER(CFTypeRef),
    num_values: int,
    callbacks
) -> CFArrayRef:
    """Create CFArray from values."""
    func = _core_foundation.CFArrayCreate
    func.argtypes = [
        CFTypeRef,  # allocator
        ctypes.POINTER(CFTypeRef),  # values
        ctypes.c_long,  # numValues
        CFTypeRef,  # callBacks
    ]
    func.restype = CFArrayRef
    return func(allocator, values, num_values, callbacks)


def CFNumberCreate(allocator, number_type: int, value_ptr) -> CFNumberRef:
    """Create CFNumber."""
    func = _core_foundation.CFNumberCreate
    func.argtypes = [CFTypeRef, ctypes.c_int, ctypes.c_void_p]
    func.restype = CFNumberRef
    return func(allocator, number_type, value_ptr)


def CFRelease(cf_object: CFTypeRef):
    """Release a Core Foundation object."""
    if cf_object:
        func = _core_foundation.CFRelease
        func.argtypes = [CFTypeRef]
        func.restype = None
        func(cf_object)


# Core Foundation constants
kCFStringEncodingUTF8 = 0x08000100
kCFNumberSInt32Type = 3

# Boolean constants (initialized later)
kCFBooleanTrue = None
kCFBooleanFalse = None


# Get standard callback pointers (initialized later)
_cf_dict_key_callbacks = None
_cf_dict_value_callbacks = None
_cf_array_callbacks = None

def get_cf_type_dictionary_key_callbacks():
    """Get kCFTypeDictionaryKeyCallBacks."""
    global _cf_dict_key_callbacks
    if _cf_dict_key_callbacks is None:
        _load_frameworks()
        _cf_dict_key_callbacks = ctypes.c_void_p.in_dll(_core_foundation, 'kCFTypeDictionaryKeyCallBacks').value
    return _cf_dict_key_callbacks


def get_cf_type_dictionary_value_callbacks():
    """Get kCFTypeDictionaryValueCallBacks."""
    global _cf_dict_value_callbacks
    if _cf_dict_value_callbacks is None:
        _load_frameworks()
        _cf_dict_value_callbacks = ctypes.c_void_p.in_dll(_core_foundation, 'kCFTypeDictionaryValueCallBacks').value
    return _cf_dict_value_callbacks


def get_cf_type_array_callbacks():
    """Get kCFTypeArrayCallBacks."""
    global _cf_array_callbacks
    if _cf_array_callbacks is None:
        _load_frameworks()
        _cf_array_callbacks = ctypes.c_void_p.in_dll(_core_foundation, 'kCFTypeArrayCallBacks').value
    return _cf_array_callbacks


# Core Audio API: AudioHardwareCreateAggregateDevice
def AudioHardwareCreateAggregateDevice(
    description: CFDictionaryRef
) -> tuple[OSStatus, AudioObjectID]:
    """
    Create an aggregate audio device.

    Args:
        description: CFDictionary describing the aggregate device

    Returns:
        Tuple of (OSStatus, AudioObjectID)
        - OSStatus: 0 on success, error code otherwise
        - AudioObjectID: Device ID of created aggregate device
    """
    ca_lib, _ = _load_frameworks()

    # Function signature:
    # OSStatus AudioHardwareCreateAggregateDevice(
    #     CFDictionaryRef inDescription,
    #     AudioObjectID* outDeviceObjectID
    # )
    func = ca_lib.AudioHardwareCreateAggregateDevice
    func.argtypes = [CFDictionaryRef, ctypes.POINTER(AudioObjectID)]
    func.restype = OSStatus

    device_id = AudioObjectID(0)
    status = func(description, ctypes.byref(device_id))

    return status, device_id.value


def AudioHardwareDestroyAggregateDevice(device_id: int) -> OSStatus:
    """
    Destroy an aggregate audio device.

    Args:
        device_id: AudioObjectID of the aggregate device

    Returns:
        OSStatus: 0 on success, error code otherwise
    """
    ca_lib, _ = _load_frameworks()

    func = ca_lib.AudioHardwareDestroyAggregateDevice
    func.argtypes = [AudioObjectID]
    func.restype = OSStatus

    return func(AudioObjectID(device_id))


# Core Audio Property Address structure
class AudioObjectPropertyAddress(ctypes.Structure):
    """AudioObjectPropertyAddress structure for Core Audio property queries."""
    _fields_ = [
        ('mSelector', ctypes.c_uint32),  # AudioObjectPropertySelector
        ('mScope', ctypes.c_uint32),     # AudioObjectPropertyScope
        ('mElement', ctypes.c_uint32),   # AudioObjectPropertyElement
    ]


# Core Audio constants
kAudioObjectSystemObject = 1
kAudioObjectPropertyScopeGlobal = 0x676C6F62  # 'glob'
kAudioObjectPropertyElementMain = 0
kAudioHardwarePropertyDefaultOutputDevice = 0x646F7574  # 'dout'
kAudioDevicePropertyDeviceUID = 0x75696420  # 'uid '
kAudioTapPropertyFormat = 0x66746170  # 'ftap'


def AudioObjectGetPropertyDataSize(
    object_id: int,
    address: AudioObjectPropertyAddress,
    qualifier_data_size: int = 0,
    qualifier_data=None
) -> tuple[OSStatus, int]:
    """
    Get the size of a property's data.

    Args:
        object_id: AudioObjectID
        address: AudioObjectPropertyAddress
        qualifier_data_size: Size of qualifier data
        qualifier_data: Qualifier data pointer

    Returns:
        Tuple of (OSStatus, data_size)
    """
    ca_lib, _ = _load_frameworks()

    func = ca_lib.AudioObjectGetPropertyDataSize
    func.argtypes = [
        AudioObjectID,
        ctypes.POINTER(AudioObjectPropertyAddress),
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint32)
    ]
    func.restype = OSStatus

    data_size = ctypes.c_uint32(0)
    status = func(
        AudioObjectID(object_id),
        ctypes.byref(address),
        qualifier_data_size,
        qualifier_data,
        ctypes.byref(data_size)
    )

    return status, data_size.value


def AudioObjectGetPropertyData(
    object_id: int,
    address: AudioObjectPropertyAddress,
    qualifier_data_size: int = 0,
    qualifier_data=None,
    data_size: int = 0
) -> tuple[OSStatus, bytes]:
    """
    Get property data from a Core Audio object.

    Args:
        object_id: AudioObjectID
        address: AudioObjectPropertyAddress
        qualifier_data_size: Size of qualifier data
        qualifier_data: Qualifier data pointer
        data_size: Expected data size (0 = query first)

    Returns:
        Tuple of (OSStatus, data_bytes)
    """
    ca_lib, _ = _load_frameworks()

    # If data_size is 0, query the size first
    if data_size == 0:
        status, data_size = AudioObjectGetPropertyDataSize(
            object_id, address, qualifier_data_size, qualifier_data
        )
        if status != 0:
            return status, b''

    # Allocate buffer for data
    data_buffer = (ctypes.c_byte * data_size)()
    io_data_size = ctypes.c_uint32(data_size)

    func = ca_lib.AudioObjectGetPropertyData
    func.argtypes = [
        AudioObjectID,
        ctypes.POINTER(AudioObjectPropertyAddress),
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_void_p
    ]
    func.restype = OSStatus

    status = func(
        AudioObjectID(object_id),
        ctypes.byref(address),
        qualifier_data_size,
        qualifier_data,
        ctypes.byref(io_data_size),
        data_buffer
    )

    if status == 0:
        return status, bytes(data_buffer[:io_data_size.value])
    else:
        return status, b''


# Audio Device I/O Types
AudioDeviceIOProcID = ctypes.c_void_p


def _convert_ioproc_id(io_proc_id):
    """Convert various IOProcID formats to ctypes pointer."""
    if io_proc_id is None:
        return AudioDeviceIOProcID(0)
    elif isinstance(io_proc_id, int):
        return AudioDeviceIOProcID(io_proc_id)
    else:
        # Try to extract pointer value from PyObjC pointer object
        try:
            # PyObjC pointers may have __int__ or value
            if hasattr(io_proc_id, '__int__'):
                return AudioDeviceIOProcID(int(io_proc_id))
            elif hasattr(io_proc_id, 'value'):
                return AudioDeviceIOProcID(io_proc_id.value)
            else:
                # Try direct conversion
                return AudioDeviceIOProcID(io_proc_id)
        except:
            # Last resort: use object ID as pointer value
            try:
                return AudioDeviceIOProcID(id(io_proc_id))
            except:
                return AudioDeviceIOProcID(0)


def AudioDeviceStart(device_id: int, io_proc_id) -> OSStatus:
    """
    Start an audio device.

    Args:
        device_id: AudioObjectID of the device
        io_proc_id: AudioDeviceIOProcID (can be None, int, or PyObjC pointer)

    Returns:
        OSStatus: 0 on success, error code otherwise
    """
    ca_lib, _ = _load_frameworks()

    func = ca_lib.AudioDeviceStart
    func.argtypes = [AudioObjectID, AudioDeviceIOProcID]
    func.restype = OSStatus

    proc_id = _convert_ioproc_id(io_proc_id)
    logger.debug(f"AudioDeviceStart: device_id={device_id}, io_proc_id={io_proc_id} -> proc_id={proc_id}")

    return func(AudioObjectID(device_id), proc_id)


def AudioDeviceStop(device_id: int, io_proc_id) -> OSStatus:
    """
    Stop an audio device.

    Args:
        device_id: AudioObjectID of the device
        io_proc_id: AudioDeviceIOProcID (can be None, int, or PyObjC pointer)

    Returns:
        OSStatus: 0 on success, error code otherwise
    """
    ca_lib, _ = _load_frameworks()

    func = ca_lib.AudioDeviceStop
    func.argtypes = [AudioObjectID, AudioDeviceIOProcID]
    func.restype = OSStatus

    proc_id = _convert_ioproc_id(io_proc_id)
    logger.debug(f"AudioDeviceStop: device_id={device_id}, io_proc_id={io_proc_id} -> proc_id={proc_id}")

    return func(AudioObjectID(device_id), proc_id)


# Helper function to create CFDictionary from Python dict
def create_cf_dictionary(py_dict: dict) -> CFDictionaryRef:
    """
    Create CFDictionary from Python dictionary.

    Keys and values are converted to CF types:
    - str → CFString
    - int → CFNumber
    - bool → CFBoolean
    - list → CFArray
    - dict → CFDictionary (recursive)

    Args:
        py_dict: Python dictionary

    Returns:
        CFDictionaryRef (must be released with CFRelease)
    """
    _load_frameworks()

    # Convert Python values to CF types
    cf_keys = []
    cf_values = []

    for key, value in py_dict.items():
        # Convert key (must be string or bytes)
        if isinstance(key, str):
            key_bytes = key.encode('utf-8')
        elif isinstance(key, bytes):
            key_bytes = key
        else:
            raise TypeError(f"Dictionary key must be str or bytes, got {type(key)}")

        cf_key = CFStringCreateWithCString(None, key_bytes, kCFStringEncodingUTF8)
        cf_keys.append(cf_key)

        # Convert value
        cf_value = _py_to_cf(value)
        cf_values.append(cf_value)

    # Create C arrays
    num_items = len(cf_keys)
    keys_array = (CFTypeRef * num_items)(*cf_keys)
    values_array = (CFTypeRef * num_items)(*cf_values)

    # Create dictionary
    cf_dict = CFDictionaryCreate(
        None,  # allocator
        keys_array,
        values_array,
        num_items,
        get_cf_type_dictionary_key_callbacks(),
        get_cf_type_dictionary_value_callbacks()
    )

    return cf_dict


def _py_to_cf(value):
    """Convert Python value to Core Foundation type."""
    if value is None:
        return None
    elif isinstance(value, bool):
        # IMPORTANT: Check bool before int (bool is subclass of int)
        return kCFBooleanTrue if value else kCFBooleanFalse
    elif isinstance(value, int):
        int_val = ctypes.c_int32(value)
        return CFNumberCreate(None, kCFNumberSInt32Type, ctypes.byref(int_val))
    elif isinstance(value, str):
        return CFStringCreateWithCString(None, value.encode('utf-8'), kCFStringEncodingUTF8)
    elif isinstance(value, bytes):
        return CFStringCreateWithCString(None, value, kCFStringEncodingUTF8)
    elif isinstance(value, list):
        cf_items = [_py_to_cf(item) for item in value]
        items_array = (CFTypeRef * len(cf_items))(*cf_items)
        return CFArrayCreate(None, items_array, len(cf_items), get_cf_type_array_callbacks())
    elif isinstance(value, dict):
        return create_cf_dictionary(value)
    else:
        raise TypeError(f"Cannot convert {type(value)} to CF type")


# High-level helper functions

def get_default_output_device_uid() -> tuple[bool, str]:
    """
    Get the UID of the default system output device using ctypes.

    Returns:
        Tuple of (success, uid_string)
        - success: True if successful, False otherwise
        - uid_string: Device UID, or empty string on failure
    """
    try:
        # Step 1: Get default output device ID
        address = AudioObjectPropertyAddress(
            mSelector=kAudioHardwarePropertyDefaultOutputDevice,
            mScope=kAudioObjectPropertyScopeGlobal,
            mElement=kAudioObjectPropertyElementMain
        )

        status, device_data = AudioObjectGetPropertyData(
            kAudioObjectSystemObject,
            address,
            data_size=4  # AudioObjectID is 4 bytes
        )

        if status != 0 or len(device_data) != 4:
            logger.error(f"Failed to get default output device: status={status}")
            return False, ""

        device_id = struct.unpack('I', device_data)[0]
        logger.debug(f"Default output device ID: {device_id}")

        # Step 2: Get device UID
        uid_address = AudioObjectPropertyAddress(
            mSelector=kAudioDevicePropertyDeviceUID,
            mScope=kAudioObjectPropertyScopeGlobal,
            mElement=kAudioObjectPropertyElementMain
        )

        status, uid_data = AudioObjectGetPropertyData(device_id, uid_address)

        if status != 0:
            logger.error(f"Failed to get device UID: status={status}")
            return False, ""

        # uid_data is CFString bytes - convert to Python string
        # CFString is stored as UTF-8 C string at the end of the CFString object
        # For simplicity, use CFStringGetCString
        uid_cfstring = CFTypeRef(ctypes.cast(ctypes.c_char_p(uid_data), ctypes.c_void_p).value)

        # Alternatively, interpret as null-terminated UTF-8 string
        # Find null terminator
        null_index = uid_data.find(b'\x00')
        if null_index > 0:
            uid_str = uid_data[:null_index].decode('utf-8')
        else:
            # Try to decode entire buffer
            uid_str = uid_data.decode('utf-8', errors='ignore').rstrip('\x00')

        logger.debug(f"Default output device UID: {uid_str}")
        return True, uid_str

    except Exception as e:
        logger.error(f"Error getting default output device UID: {e}")
        import traceback
        traceback.print_exc()
        return False, ""


def read_tap_stream_format(tap_device_id: int) -> tuple[bool, dict]:
    """
    Read the stream format of a Process Tap device (CRITICAL for AudioCap).

    This function reads the kAudioTapPropertyFormat property, which returns
    an AudioStreamBasicDescription structure. This read is CRITICAL and must
    be done BEFORE creating the Aggregate Device (AudioCap line 133).

    Args:
        tap_device_id: AudioObjectID of the tap device

    Returns:
        Tuple of (success, format_dict)
        - success: True if successful, False otherwise
        - format_dict: Dictionary with 'sample_rate', 'channels', 'bits_per_channel'
    """
    try:
        # Create property address for tap stream format
        address = AudioObjectPropertyAddress(
            mSelector=kAudioTapPropertyFormat,
            mScope=kAudioObjectPropertyScopeGlobal,
            mElement=kAudioObjectPropertyElementMain
        )

        # AudioStreamBasicDescription is 40 bytes:
        # - mSampleRate: Float64 (8 bytes)
        # - mFormatID: UInt32 (4 bytes)
        # - mFormatFlags: UInt32 (4 bytes)
        # - mBytesPerPacket: UInt32 (4 bytes)
        # - mFramesPerPacket: UInt32 (4 bytes)
        # - mBytesPerFrame: UInt32 (4 bytes)
        # - mChannelsPerFrame: UInt32 (4 bytes)
        # - mBitsPerChannel: UInt32 (4 bytes)
        # - mReserved: UInt32 (4 bytes)

        status, format_data = AudioObjectGetPropertyData(
            tap_device_id,
            address,
            data_size=40
        )

        if status != 0:
            logger.error(f"Failed to read tap stream format: status={status}")
            return False, {}

        if len(format_data) < 40:
            logger.error(f"Tap format data too small: {len(format_data)} bytes")
            return False, {}

        # Parse AudioStreamBasicDescription
        import struct as st
        sample_rate, format_id, format_flags, bytes_per_packet, frames_per_packet, \
        bytes_per_frame, channels_per_frame, bits_per_channel, reserved = st.unpack(
            '<dIIIIIIII', format_data[:40]
        )

        format_dict = {
            'sample_rate': sample_rate,
            'format_id': format_id,
            'format_flags': format_flags,
            'bytes_per_packet': bytes_per_packet,
            'frames_per_packet': frames_per_packet,
            'bytes_per_frame': bytes_per_frame,
            'channels': channels_per_frame,
            'bits_per_channel': bits_per_channel,
        }

        logger.info(
            f"✅ [CRITICAL] Tap stream format read successfully: "
            f"{sample_rate:.0f} Hz, {channels_per_frame} channels, "
            f"{bits_per_channel} bits/sample"
        )

        return True, format_dict

    except Exception as e:
        logger.error(f"Error reading tap stream format: {e}")
        import traceback
        traceback.print_exc()
        return False, {}


# Initialize frameworks on import
try:
    _load_frameworks()
    # Get constants
    kCFBooleanTrue = ctypes.c_void_p.in_dll(_core_foundation, 'kCFBooleanTrue').value
    kCFBooleanFalse = ctypes.c_void_p.in_dll(_core_foundation, 'kCFBooleanFalse').value
    logger.debug(f"Core Audio ctypes bindings initialized (kCFBooleanTrue={kCFBooleanTrue}, kCFBooleanFalse={kCFBooleanFalse})")
except Exception as e:
    logger.warning(f"Failed to initialize Core Audio ctypes bindings: {e}")
    kCFBooleanTrue = None
    kCFBooleanFalse = None


# TCC Permission Helper

def check_audio_capture_permission() -> tuple[bool, str]:
    """
    Check if the application has audio capture (microphone) permission.

    NOTE: This check is based on AVFoundation microphone access, which is more
    reliable than Core Audio property access. Process Tap API requires
    AVFoundation microphone permission, not Core Audio property access.

    Returns:
        Tuple of (has_permission, message)
    """
    try:
        # Check AVFoundation microphone permission (most reliable)
        try:
            from AVFoundation import AVCaptureDevice, AVMediaTypeAudio
            device = AVCaptureDevice.defaultDeviceWithMediaType_(AVMediaTypeAudio)
            if device:
                return True, "AVFoundation microphone permission granted"
            else:
                return False, "AVFoundation cannot access microphone"
        except ImportError:
            # AVFoundation not available, assume permission needed
            logger.warning("AVFoundation not available for permission check")
            return False, "AVFoundation not available - install pyobjc-framework-AVFoundation"
        except Exception as e:
            logger.debug(f"AVFoundation permission check error: {e}")
            return False, f"AVFoundation error: {e}"

    except Exception as e:
        return False, f"Error checking permission: {e}"


def request_microphone_permission() -> bool:
    """
    Request microphone permission from the user.

    This will trigger the macOS system dialog asking for microphone access.
    The dialog will only appear once per application.

    Returns:
        True if permission was granted, False otherwise
    """
    try:
        import subprocess
        import time

        logger.info("Requesting microphone permission...")

        # Method 1: Try PyObjC AVFoundation (most reliable for triggering dialog)
        try:
            from AVFoundation import AVCaptureDevice, AVMediaTypeAudio

            logger.debug("Attempting to request microphone permission via PyObjC AVFoundation...")

            # This call triggers the TCC permission dialog
            device = AVCaptureDevice.defaultDeviceWithMediaType_(AVMediaTypeAudio)

            # Wait for the dialog to be shown and dismissed
            time.sleep(1.0)

            # Check if permission was granted
            has_permission, _ = check_audio_capture_permission()
            if has_permission:
                logger.info("Permission granted via PyObjC AVFoundation")
                return True

            logger.debug("Permission not granted after PyObjC AVFoundation request")

        except ImportError:
            logger.debug("PyObjC AVFoundation not available, trying alternative methods...")
        except Exception as e:
            logger.debug(f"PyObjC AVFoundation method failed: {e}")

        # Method 2: Try AppleScript with AVFoundation framework
        try:
            logger.debug("Attempting AppleScript with AVFoundation...")

            # Use AppleScript to load AVFoundation and request audio device
            applescript = '''
use framework "AVFoundation"
use scripting additions

on run
    try
        set audioDevice to current application's AVCaptureDevice's defaultDeviceWithMediaType:(current application's AVMediaTypeAudio)
        if audioDevice is not missing value then
            return "granted"
        else
            return "no_device"
        end if
    on error errMsg
        return "error: " & errMsg
    end try
end run
'''

            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=30
            )

            logger.debug(f"AppleScript result: {result.stdout.strip()}")

            time.sleep(1.0)
            has_permission, _ = check_audio_capture_permission()
            if has_permission:
                logger.info("Permission granted via AppleScript")
                return True

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug(f"AppleScript method failed: {e}")
        except Exception as e:
            logger.debug(f"AppleScript error: {e}")

        # Method 3: Try JavaScript for Automation (JXA)
        try:
            logger.debug("Attempting JXA with AVFoundation...")

            jxa_code = '''
const app = Application.currentApplication();
app.includeStandardAdditions = true;

ObjC.import('AVFoundation');

try {
    const device = $.AVCaptureDevice.defaultDeviceWithMediaType($.AVMediaTypeAudio);
    if (device) {
        "granted";
    } else {
        "no_device";
    }
} catch (e) {
    "error: " + e.toString();
}
'''

            result = subprocess.run(
                ['osascript', '-l', 'JavaScript', '-e', jxa_code],
                capture_output=True,
                text=True,
                timeout=30
            )

            logger.debug(f"JXA result: {result.stdout.strip()}")

            time.sleep(1.0)
            has_permission, _ = check_audio_capture_permission()
            if has_permission:
                logger.info("Permission granted via JXA")
                return True

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug(f"JXA method failed: {e}")
        except Exception as e:
            logger.debug(f"JXA error: {e}")

        # All methods failed to trigger dialog or grant permission
        logger.warning("All permission request methods failed or were denied")
        return False

    except Exception as e:
        logger.error(f"Error requesting microphone permission: {e}")
        import traceback
        traceback.print_exc()
        return False


def open_system_preferences_privacy():
    """
    Open System Settings (or System Preferences) to the Privacy & Security → Microphone page.

    This helps the user quickly navigate to the correct settings page.
    """
    try:
        import subprocess

        logger.info("Opening System Settings/Preferences...")

        # Try new System Settings URL (macOS 13+)
        subprocess.run([
            'open',
            'x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone'
        ], check=False)

        print("\n✅ Opening System Settings → Privacy & Security → Microphone")
        print("   Please enable the checkbox for Terminal/Python/Your IDE")
        print()

        return True

    except Exception as e:
        logger.error(f"Error opening System Settings: {e}")
        return False


def print_tcc_help(auto_open: bool = True):
    """
    Print instructions for granting TCC permissions.

    Args:
        auto_open: If True, automatically open System Settings
    """
    print("\n" + "="*70)
    print("🔒 Microphone Permission Required")
    print("="*70)
    print()
    print("This application needs 'Microphone' access to capture process audio.")
    print()

    if auto_open:
        print("Opening System Settings for you...")
        print()
        success = open_system_preferences_privacy()

        if success:
            print("Please:")
            print("  1. Look for the System Settings window that just opened")
            print("  2. Find and enable the checkbox for:")
            print("     • Terminal (if running from terminal)")
            print("     • Python (if running directly)")
            print("     • Your IDE (if running from IDE)")
            print()
            print("After granting permission, run this application again.")
        else:
            print("Could not auto-open System Settings. Please open manually:")
    else:
        print("To grant permission:")

    if not auto_open or not success:
        print("  1. Open 'System Settings' (or 'System Preferences' on older macOS)")
        print("  2. Go to 'Privacy & Security' → 'Microphone'")
        print("  3. Enable the checkbox for:")
        print("     • Terminal (if running from terminal)")
        print("     • Python (if running directly)")
        print("     • Your IDE (if running from IDE)")
        print()
        print("After granting permission, run this application again.")

    print("="*70)
    print()


def ensure_microphone_permission(auto_request: bool = True, auto_open_settings: bool = True) -> bool:
    """
    Ensure microphone permission is granted, requesting if necessary.

    This is the main function to call at application startup.

    Args:
        auto_request: If True, automatically request permission if not granted
        auto_open_settings: If True, open System Settings if permission denied

    Returns:
        True if permission is granted, False otherwise
    """
    # Check current permission status
    has_permission, msg = check_audio_capture_permission()

    if has_permission:
        logger.info("✅ Microphone permission already granted")
        return True

    logger.warning(f"⚠️  Microphone permission not granted: {msg}")

    # Try to request permission
    if auto_request:
        print("\n🎤 Requesting microphone permission...")
        print("A system dialog may appear - please click 'OK' or 'Allow'\n")

        if request_microphone_permission():
            logger.info("✅ Microphone permission granted!")
            print("✅ Permission granted successfully!\n")
            return True
        else:
            logger.warning("❌ Microphone permission was denied or dialog not shown")

    # Permission not granted - show help
    print_tcc_help(auto_open=auto_open_settings)

    return False
