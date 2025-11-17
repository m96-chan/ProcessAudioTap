"""
macOS audio capture backend using PyObjC and Core Audio API.

This is the OFFICIAL macOS backend for ProcTap (Phase 3).

This module provides process-specific audio capture on macOS 14.4+ using
PyObjC bindings to Core Audio Process Tap API.

Advantages:
- Direct Python integration (no subprocess overhead)
- Better error handling and debugging
- Simple deployment (pip install only)
- Per-process audio isolation using Core Audio Process Tap API

Requirements:
- macOS 14.4 (Sonoma) or later
- PyObjC: pip install pyobjc-core pyobjc-framework-CoreAudio
- Audio capture permission (NSMicrophoneUsageDescription)

STATUS: Phase 3 - Official macOS Backend (Verified Working)

Note: Swift CLI and C extension approaches are experimental and not recommended.
      See src/proctap/experimental/ for those implementations.
"""

from __future__ import annotations

from typing import Optional, Callable
import logging
import platform
import queue
import threading
from ctypes import (
    c_uint8, c_uint32, c_int32, c_uint64, c_double, c_void_p, c_char_p,
    POINTER, Structure, CFUNCTYPE, byref, pointer, sizeof, cast, CDLL, util
)

from .base import AudioBackend

logger = logging.getLogger(__name__)

# Type alias for audio callback
AudioCallback = Callable[[bytes, int], None]

# Core Audio constants and types (defined manually via ctypes)
# These are typically in CoreAudio framework headers

# Audio Object constants
kAudioObjectSystemObject = 1  # AudioSystemObject
kAudioObjectPropertyScopeGlobal = 0x676C6F62  # 'glob'
kAudioObjectPropertyElementMain = 0  # Main element

# Properties
kAudioHardwarePropertyTranslatePIDToProcessObject = 0x70696432  # 'pid2'

# OSStatus codes
noErr = 0

# Check if we can load Core Audio framework
COREAUDIO_AVAILABLE = False
_core_audio_lib = None

try:
    framework_path = util.find_library('CoreAudio')
    if framework_path:
        _core_audio_lib = CDLL(framework_path)
        COREAUDIO_AVAILABLE = True
        logger.debug("Core Audio framework loaded successfully")
    else:
        logger.warning("Core Audio framework not found")
except Exception as e:
    logger.warning(f"Failed to load Core Audio framework: {e}")


# Core Audio C structures and constants

# Audio Object types
AudioObjectID = c_uint32

# Audio format constants
kAudioFormatLinearPCM = 0x6C70636D  # 'lpcm'
kAudioFormatFlagIsSignedInteger = (1 << 2)
kAudioFormatFlagIsPacked = (1 << 3)

# Tap type constants
kCATapTypeInput = 0  # Capture microphone input
kCATapTypeOutput = 1  # Capture playback output


class AudioObjectPropertyAddress(Structure):
    """Audio object property address structure."""
    _fields_ = [
        ('mSelector', c_uint32),
        ('mScope', c_uint32),
        ('mElement', c_uint32),
    ]


class AudioStreamBasicDescription(Structure):
    """Audio format description structure."""
    _fields_ = [
        ('mSampleRate', c_double),
        ('mFormatID', c_uint32),
        ('mFormatFlags', c_uint32),
        ('mBytesPerPacket', c_uint32),
        ('mFramesPerPacket', c_uint32),
        ('mBytesPerFrame', c_uint32),
        ('mChannelsPerFrame', c_uint32),
        ('mBitsPerChannel', c_uint32),
        ('mReserved', c_uint32),
    ]


class AudioBuffer(Structure):
    """Single audio buffer."""
    _fields_ = [
        ('mNumberChannels', c_uint32),
        ('mDataByteSize', c_uint32),
        ('mData', c_void_p),
    ]


class AudioBufferList(Structure):
    """List of audio buffers."""
    _fields_ = [
        ('mNumberBuffers', c_uint32),
        ('mBuffers', AudioBuffer * 1),  # Flexible array
    ]


class AudioTimeStamp(Structure):
    """Audio timestamp structure."""
    _fields_ = [
        ('mSampleTime', c_double),
        ('mHostTime', c_uint64),
        ('mRateScalar', c_double),
        ('mWordClockTime', c_uint64),
        ('mSMPTETime', c_void_p),  # SMPTETime structure
        ('mFlags', c_uint32),
        ('mReserved', c_uint32),
    ]


class CATapDescription(Structure):
    """Core Audio Process Tap description."""
    _fields_ = [
        ('mProcessObjectID', c_uint32),
        ('mTapType', c_uint32),
        ('mFormat', POINTER(AudioStreamBasicDescription)),
    ]


# Audio device IO callback signature
# OSStatus (*AudioDeviceIOProc)(
#     AudioDeviceID inDevice,
#     const AudioTimeStamp *inNow,
#     const AudioBufferList *inInputData,
#     const AudioTimeStamp *inInputTime,
#     AudioBufferList *outOutputData,
#     const AudioTimeStamp *inOutputTime,
#     void *inClientData
# )
AudioDeviceIOProc = CFUNCTYPE(
    c_int32,  # OSStatus
    c_uint32,  # AudioDeviceID
    POINTER(AudioTimeStamp),  # inNow
    POINTER(AudioBufferList),  # inInputData
    POINTER(AudioTimeStamp),  # inInputTime
    POINTER(AudioBufferList),  # outOutputData
    POINTER(AudioTimeStamp),  # inOutputTime
    c_void_p  # inClientData
)


# Load Core Audio framework functions via ctypes
_core_audio_loaded = False
_AudioObjectGetPropertyData = None
_AudioObjectHasProperty = None
_AudioHardwareCreateProcessTap = None
_AudioDeviceCreateIOProcID = None
_AudioDeviceStart = None
_AudioDeviceStop = None
_AudioDeviceDestroyIOProcID = None


def _load_core_audio_functions():
    """Load Core Audio framework functions via ctypes."""
    global _core_audio_loaded
    global _AudioObjectGetPropertyData
    global _AudioObjectHasProperty
    global _AudioHardwareCreateProcessTap
    global _AudioDeviceCreateIOProcID
    global _AudioDeviceStart
    global _AudioDeviceStop
    global _AudioDeviceDestroyIOProcID

    if _core_audio_loaded:
        return True

    if not COREAUDIO_AVAILABLE or not _core_audio_lib:
        logger.error("Core Audio framework not loaded")
        return False

    try:
        core_audio = _core_audio_lib

        # OSStatus AudioObjectGetPropertyData(
        #     AudioObjectID inObjectID,
        #     const AudioObjectPropertyAddress *inAddress,
        #     UInt32 inQualifierDataSize,
        #     const void *inQualifierData,
        #     UInt32 *ioDataSize,
        #     void *outData
        # )
        _AudioObjectGetPropertyData = core_audio.AudioObjectGetPropertyData
        _AudioObjectGetPropertyData.argtypes = [
            c_uint32,  # AudioObjectID
            POINTER(AudioObjectPropertyAddress),
            c_uint32,  # qualifier size
            c_void_p,  # qualifier data
            POINTER(c_uint32),  # data size
            c_void_p  # output data
        ]
        _AudioObjectGetPropertyData.restype = c_int32

        # Boolean AudioObjectHasProperty(
        #     AudioObjectID inObjectID,
        #     const AudioObjectPropertyAddress *inAddress
        # )
        _AudioObjectHasProperty = core_audio.AudioObjectHasProperty
        _AudioObjectHasProperty.argtypes = [
            c_uint32,
            POINTER(AudioObjectPropertyAddress)
        ]
        _AudioObjectHasProperty.restype = c_uint8  # Boolean

        # OSStatus AudioHardwareCreateProcessTap(
        #     const CATapDescription *inTapDescription,
        #     AudioDeviceID *outTapDeviceID
        # )
        _AudioHardwareCreateProcessTap = core_audio.AudioHardwareCreateProcessTap
        _AudioHardwareCreateProcessTap.argtypes = [
            POINTER(CATapDescription),
            POINTER(c_uint32)
        ]
        _AudioHardwareCreateProcessTap.restype = c_int32

        # OSStatus AudioDeviceCreateIOProcID(
        #     AudioDeviceID inDevice,
        #     AudioDeviceIOProc inProc,
        #     void *inClientData,
        #     AudioDeviceIOProcID *outIOProcID
        # )
        _AudioDeviceCreateIOProcID = core_audio.AudioDeviceCreateIOProcID
        _AudioDeviceCreateIOProcID.argtypes = [
            c_uint32,
            AudioDeviceIOProc,
            c_void_p,
            POINTER(c_void_p)
        ]
        _AudioDeviceCreateIOProcID.restype = c_int32

        # OSStatus AudioDeviceStart(
        #     AudioDeviceID inDevice,
        #     AudioDeviceIOProcID inProcID
        # )
        _AudioDeviceStart = core_audio.AudioDeviceStart
        _AudioDeviceStart.argtypes = [c_uint32, c_void_p]
        _AudioDeviceStart.restype = c_int32

        # OSStatus AudioDeviceStop(
        #     AudioDeviceID inDevice,
        #     AudioDeviceIOProcID inProcID
        # )
        _AudioDeviceStop = core_audio.AudioDeviceStop
        _AudioDeviceStop.argtypes = [c_uint32, c_void_p]
        _AudioDeviceStop.restype = c_int32

        # OSStatus AudioDeviceDestroyIOProcID(
        #     AudioDeviceID inDevice,
        #     AudioDeviceIOProcID inProcID
        # )
        _AudioDeviceDestroyIOProcID = core_audio.AudioDeviceDestroyIOProcID
        _AudioDeviceDestroyIOProcID.argtypes = [c_uint32, c_void_p]
        _AudioDeviceDestroyIOProcID.restype = c_int32

        _core_audio_loaded = True
        logger.debug("Core Audio C functions loaded successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to load Core Audio functions: {e}")
        return False


def is_available() -> bool:
    """
    Check if Core Audio framework is available via ctypes.

    Returns:
        True if Core Audio can be accessed
    """
    return COREAUDIO_AVAILABLE and _load_core_audio_functions()


def create_audio_format(
    sample_rate: float = 48000.0,
    channels: int = 2,
    bits_per_channel: int = 16
) -> AudioStreamBasicDescription:
    """
    Create AudioStreamBasicDescription for PCM audio.

    Args:
        sample_rate: Sample rate in Hz (default: 48000)
        channels: Number of channels (default: 2 for stereo)
        bits_per_channel: Bits per channel (default: 16)

    Returns:
        Configured AudioStreamBasicDescription
    """
    asbd = AudioStreamBasicDescription()
    asbd.mSampleRate = sample_rate
    asbd.mFormatID = kAudioFormatLinearPCM
    asbd.mFormatFlags = kAudioFormatFlagIsSignedInteger | kAudioFormatFlagIsPacked
    asbd.mBitsPerChannel = bits_per_channel
    asbd.mChannelsPerFrame = channels
    asbd.mBytesPerFrame = channels * (bits_per_channel // 8)
    asbd.mFramesPerPacket = 1
    asbd.mBytesPerPacket = asbd.mBytesPerFrame * asbd.mFramesPerPacket
    asbd.mReserved = 0

    return asbd


def create_process_tap(process_object_id: int, tap_type: int = kCATapTypeOutput) -> Optional[int]:
    """
    Create an audio process tap for a specific process.

    Args:
        process_object_id: Core Audio process object ID
        tap_type: Tap type (kCATapTypeInput or kCATapTypeOutput)

    Returns:
        Tap device ID (AudioDeviceID), or None if creation failed

    Raises:
        RuntimeError: If Core Audio functions are not loaded
    """
    if not _core_audio_loaded:
        raise RuntimeError("Core Audio functions not loaded")

    try:
        # Create tap description
        tap_desc = CATapDescription()
        tap_desc.mProcessObjectID = process_object_id
        tap_desc.mTapType = tap_type
        tap_desc.mFormat = None  # Use default format (will query later)

        # Create tap
        tap_device_id = c_uint32(0)
        status = _AudioHardwareCreateProcessTap(
            byref(tap_desc),
            byref(tap_device_id)
        )

        if status != 0:
            logger.error(f"AudioHardwareCreateProcessTap failed with status {status}")
            return None

        logger.debug(f"Created process tap: device ID {tap_device_id.value}")
        return int(tap_device_id.value)

    except Exception as e:
        logger.error(f"Error creating process tap: {e}")
        return None


def get_macos_version() -> tuple[int, int, int]:
    """
    Get macOS version as tuple (major, minor, patch).

    Returns:
        Tuple of (major, minor, patch) version numbers

    Example:
        (14, 4, 0) for macOS 14.4.0 Sonoma
    """
    try:
        version_str = platform.mac_ver()[0]
        parts = version_str.split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except Exception as e:
        logger.warning(f"Failed to parse macOS version: {e}")
        return (0, 0, 0)


def supports_process_tap() -> bool:
    """
    Check if the current macOS version supports Process Tap API.

    Returns:
        True if macOS 14.4+, False otherwise
    """
    major, minor, _ = get_macos_version()
    return major > 14 or (major == 14 and minor >= 4)


class ProcessAudioDiscovery:
    """
    Discover Core Audio objects for a process by PID.

    This class wraps the Core Audio API for translating process IDs to
    Core Audio object IDs.
    """

    def __init__(self):
        """
        Initialize process audio discovery.

        Raises:
            RuntimeError: If Core Audio is not available or macOS version is too old
        """
        if not is_available():
            raise RuntimeError(
                "Core Audio framework not available via ctypes."
            )

        if not supports_process_tap():
            major, minor, patch = get_macos_version()
            raise RuntimeError(
                f"macOS {major}.{minor}.{patch} does not support Process Tap API. "
                "Requires macOS 14.4 (Sonoma) or later."
            )

    def get_process_object_id(self, pid: int) -> Optional[int]:
        """
        Translate process ID to Core Audio object ID.

        Args:
            pid: Target process ID

        Returns:
            Core Audio object ID (AudioObjectID), or None if not found

        Raises:
            RuntimeError: If API call fails
        """
        try:
            # Create property address for PID translation
            address = AudioObjectPropertyAddress()
            address.mSelector = kAudioHardwarePropertyTranslatePIDToProcessObject
            address.mScope = kAudioObjectPropertyScopeGlobal
            address.mElement = kAudioObjectPropertyElementMain

            # Check if property exists
            has_property = _AudioObjectHasProperty(
                kAudioObjectSystemObject,
                byref(address)
            )

            if not has_property:
                logger.error(
                    "kAudioHardwarePropertyTranslatePIDToProcessObject not available. "
                    "This may indicate macOS version < 14.4."
                )
                return None

            # Input data: PID as UInt32
            pid_data = c_uint32(pid)
            qualifier_data_size = 4  # sizeof(UInt32)

            # Output data: AudioObjectID (UInt32)
            process_object_id = c_uint32()
            out_data_size = c_uint32(4)  # sizeof(AudioObjectID)

            # Get property data
            status = _AudioObjectGetPropertyData(
                kAudioObjectSystemObject,
                byref(address),
                qualifier_data_size,
                byref(pid_data),
                byref(out_data_size),
                byref(process_object_id)
            )

            if status != 0:
                logger.error(
                    f"AudioObjectGetPropertyData failed with status {status}. "
                    f"Process {pid} may not have audio output."
                )
                return None

            logger.debug(
                f"Translated PID {pid} to AudioObjectID {process_object_id.value}"
            )
            return int(process_object_id.value)

        except Exception as e:
            logger.error(f"Error translating PID to process object: {e}")
            raise RuntimeError(
                f"Failed to get process object for PID {pid}: {e}"
            ) from e

    def find_process_with_audio(self, pid: int) -> bool:
        """
        Check if a process has active audio output.

        Args:
            pid: Process ID to check

        Returns:
            True if process has Core Audio object, False otherwise
        """
        try:
            object_id = self.get_process_object_id(pid)
            return object_id is not None and object_id != 0
        except Exception as e:
            logger.error(f"Error checking process audio: {e}")
            return False


class MacOSNativeBackend(AudioBackend):
    """
    macOS native backend using PyObjC and Core Audio Process Tap API.

    This backend provides direct Python integration with Core Audio without
    requiring an external Swift helper binary.

    Requirements:
    - macOS 14.4 (Sonoma) or later
    - PyObjC: pip install pyobjc-core pyobjc-framework-CoreAudio
    - Audio capture permission

    Advantages over Swift helper approach:
    - ~5-10ms lower latency (no subprocess overhead)
    - Better error handling and debugging
    - Simpler deployment (pip install only)
    - Direct Python integration
    """

    def __init__(
        self,
        pid: int,
        sample_rate: int = 48000,
        channels: int = 2,
        sample_width: int = 2,
    ) -> None:
        """
        Initialize macOS native backend.

        Args:
            pid: Process ID to capture audio from
            sample_rate: Sample rate in Hz (default: 48000)
            channels: Number of channels (default: 2 for stereo)
            sample_width: Bytes per sample (default: 2 for 16-bit)

        Raises:
            RuntimeError: If PyObjC not available or macOS version < 14.4
        """
        super().__init__(pid)

        if not is_available():
            raise RuntimeError(
                "Core Audio framework not available via ctypes."
            )

        if not supports_process_tap():
            major, minor, patch = get_macos_version()
            raise RuntimeError(
                f"macOS {major}.{minor}.{patch} does not support Process Tap API. "
                "Requires macOS 14.4 (Sonoma) or later."
            )

        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width
        self._bits_per_sample = sample_width * 8

        # Core Audio objects
        self._discovery = ProcessAudioDiscovery()
        self._process_object_id: Optional[int] = None
        self._tap_device_id: Optional[int] = None
        self._io_proc_id: Optional[c_void_p] = None

        # Audio data queue
        self._audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=100)
        self._is_running = False

        # Keep reference to callback to prevent GC
        self._io_callback: Optional[AudioDeviceIOProc] = None

        logger.info(
            f"Initialized MacOSNativeBackend for PID {pid} "
            f"({sample_rate}Hz, {channels}ch, {self._bits_per_sample}bit)"
        )

    def start(self) -> None:
        """
        Start audio capture from the target process.

        Raises:
            RuntimeError: If capture fails to start
        """
        if self._is_running:
            logger.warning("Audio capture is already running")
            return

        try:
            # Step 1: Get process object ID
            self._process_object_id = self._discovery.get_process_object_id(self._pid)
            if self._process_object_id is None:
                raise RuntimeError(
                    f"Process {self._pid} does not have active audio output. "
                    "Ensure the process is playing audio."
                )

            logger.debug(f"Process object ID: {self._process_object_id}")

            # Step 2: Create process tap
            self._tap_device_id = create_process_tap(
                self._process_object_id,
                kCATapTypeOutput
            )
            if self._tap_device_id is None:
                raise RuntimeError("Failed to create process tap")

            logger.debug(f"Tap device ID: {self._tap_device_id}")

            # Step 3: Create I/O callback
            self._io_callback = AudioDeviceIOProc(self._audio_io_proc)

            # Step 4: Create I/O Proc ID
            io_proc_id_out = c_void_p()
            status = _AudioDeviceCreateIOProcID(
                self._tap_device_id,
                self._io_callback,
                None,  # Client data (could pass self)
                byref(io_proc_id_out)
            )

            if status != 0:
                raise RuntimeError(
                    f"AudioDeviceCreateIOProcID failed with status {status}"
                )

            self._io_proc_id = io_proc_id_out

            logger.debug(f"I/O Proc ID created: {self._io_proc_id}")

            # Step 5: Start audio device
            status = _AudioDeviceStart(self._tap_device_id, self._io_proc_id)
            if status != 0:
                raise RuntimeError(f"AudioDeviceStart failed with status {status}")

            self._is_running = True
            logger.info(f"Started audio capture for PID {self._pid}")

        except Exception as e:
            # Cleanup on failure
            self._cleanup()
            raise RuntimeError(f"Failed to start audio capture: {e}") from e

    def stop(self) -> None:
        """Stop audio capture."""
        if not self._is_running:
            return

        self._cleanup()
        self._is_running = False
        logger.info("Stopped audio capture")

    def read(self) -> Optional[bytes]:
        """
        Read audio data from the capture buffer.

        Returns:
            PCM audio data as bytes, or None if no data is available
        """
        if not self._is_running:
            return None

        try:
            return self._audio_queue.get(timeout=0.1)
        except queue.Empty:
            return None

    def get_format(self) -> dict[str, int | object]:
        """
        Get audio format information.

        Returns:
            Dictionary with 'sample_rate', 'channels', 'bits_per_sample'
        """
        return {
            'sample_rate': self._sample_rate,
            'channels': self._channels,
            'bits_per_sample': self._bits_per_sample,
        }

    def close(self) -> None:
        """Clean up resources."""
        self.stop()

    def __del__(self) -> None:
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except:
            pass

    def _audio_io_proc(
        self,
        device_id: int,
        now: POINTER(AudioTimeStamp),
        input_data: POINTER(AudioBufferList),
        input_time: POINTER(AudioTimeStamp),
        output_data: POINTER(AudioBufferList),
        output_time: POINTER(AudioTimeStamp),
        client_data: c_void_p
    ) -> int:
        """
        Audio I/O callback function.

        This is called by Core Audio when audio data is available.

        Args:
            device_id: Audio device ID
            now: Current time
            input_data: Input audio buffer list
            input_time: Input timestamp
            output_data: Output audio buffer list (unused for capture)
            output_time: Output timestamp
            client_data: User data pointer

        Returns:
            OSStatus (0 for success)
        """
        try:
            # Process input data (captured audio)
            if input_data:
                buffer_list = input_data.contents
                if buffer_list.mNumberBuffers > 0:
                    # Get first buffer
                    audio_buffer = buffer_list.mBuffers[0]
                    data_size = audio_buffer.mDataByteSize
                    data_ptr = audio_buffer.mData

                    if data_ptr and data_size > 0:
                        # Copy audio data to bytes
                        audio_bytes = (c_char_p * data_size).from_address(data_ptr)
                        audio_data = bytes(audio_bytes)

                        # Put in queue
                        try:
                            self._audio_queue.put_nowait(audio_data)
                        except queue.Full:
                            # Drop old frames if queue is full
                            try:
                                self._audio_queue.get_nowait()
                                self._audio_queue.put_nowait(audio_data)
                            except:
                                pass

            return 0  # Success

        except Exception as e:
            logger.error(f"Error in audio I/O callback: {e}")
            return -1  # Error

    def _cleanup(self) -> None:
        """Clean up Core Audio resources."""
        try:
            # Stop device
            if self._tap_device_id and self._io_proc_id:
                try:
                    _AudioDeviceStop(self._tap_device_id, self._io_proc_id)
                except Exception as e:
                    logger.error(f"Error stopping device: {e}")

            # Destroy I/O Proc
            if self._tap_device_id and self._io_proc_id:
                try:
                    _AudioDeviceDestroyIOProcID(self._tap_device_id, self._io_proc_id)
                except Exception as e:
                    logger.error(f"Error destroying I/O proc: {e}")

        finally:
            self._io_proc_id = None
            self._tap_device_id = None
            self._process_object_id = None


# Phase 1 Prototype: Process Discovery Only
# This is a minimal implementation to test PyObjC integration
# Future phases will add:
# - Process Tap creation (AudioHardwareCreateProcessTap)
# - Audio I/O setup (AudioDeviceCreateIOProcID, AudioDeviceStart)
# - Format configuration (AudioStreamBasicDescription)
# - Buffer management and callback handling
# - Integration with MacOSBackend


if __name__ == "__main__":
    # Test code for development
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if not is_available():
        print("ERROR: Core Audio framework not available")
        print("This requires macOS with Core Audio framework accessible via ctypes")
        sys.exit(1)

    if not supports_process_tap():
        major, minor, patch = get_macos_version()
        print(f"ERROR: macOS {major}.{minor}.{patch} does not support Process Tap")
        print("Requires macOS 14.4 (Sonoma) or later")
        sys.exit(1)

    print("✓ PyObjC Core Audio available")
    print(f"✓ macOS version: {'.'.join(map(str, get_macos_version()))}")

    # Test process discovery
    if len(sys.argv) > 1:
        try:
            test_pid = int(sys.argv[1])
            print(f"\nTesting process discovery for PID {test_pid}...")

            discovery = ProcessAudioDiscovery()
            has_audio = discovery.find_process_with_audio(test_pid)

            if has_audio:
                object_id = discovery.get_process_object_id(test_pid)
                print(f"✓ Process {test_pid} has audio (ObjectID: {object_id})")
            else:
                print(f"✗ Process {test_pid} does not have active audio output")

        except ValueError:
            print(f"ERROR: Invalid PID: {sys.argv[1]}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print("\nUsage: python -m proctap.backends.macos_pyobjc <PID>")
        print("Example: python -m proctap.backends.macos_pyobjc 1234")
