#!/usr/bin/env python3.12
"""Test IOProc directly on Tap device (bypass Aggregate)."""

import sys
import time
import queue
import objc

sys.path.insert(0, 'src')

from proctap.backends.macos_pyobjc import ProcessAudioDiscovery
from CoreAudio import (
    AudioHardwareCreateProcessTap,
    AudioDeviceCreateIOProcID,
    AudioDeviceStart,
    AudioDeviceStop,
    AudioDeviceDestroyIOProcID
)
from Foundation import NSArray, NSNumber, NSUUID
import uuid

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_ioproc_on_tap.py <PID>")
        return 1

    pid = int(sys.argv[1])
    print(f'\n🧪 Testing IOProc DIRECTLY on Tap Device (PID {pid})')
    print('='*70)
    print()

    try:
        # Step 1: Find process
        print("1. Finding process audio object...")
        discovery = ProcessAudioDiscovery()
        process_object_id = discovery.get_process_object_id(pid)

        if not process_object_id:
            print(f"❌ Process {pid} has no audio")
            return 1

        print(f"✓ Process audio object ID: {process_object_id}")
        print()

        # Step 2: Create Process Tap
        print("2. Creating Process Tap...")
        CATapDescription = objc.lookUpClass('CATapDescription')

        process_array = NSArray.arrayWithObject_(
            NSNumber.numberWithUnsignedInt_(process_object_id)
        )

        tap_desc = CATapDescription.alloc().initStereoMixdownOfProcesses_(process_array)
        tap_uuid = str(uuid.uuid4())
        tap_desc.setUUID_(NSUUID.alloc().initWithUUIDString_(tap_uuid))

        status, tap_device_id = AudioHardwareCreateProcessTap(tap_desc, None)

        if status != 0 or tap_device_id == 0:
            print(f"❌ Failed to create tap: status={status}, device_id={tap_device_id}")
            return 1

        print(f"✓ Process Tap created: Device ID {tap_device_id}")
        print()

        # Step 3: Create IOProc for TAP device (not aggregate!)
        print("3. Registering IOProc on TAP device (experimental)...")

        audio_queue = queue.Queue(maxsize=100)
        callback_count = [0]

        @objc.callbackFor(AudioDeviceCreateIOProcID)
        def tap_io_proc_callback(device_id, now, input_data, input_time, output_data, output_time, client_data):
            """IOProc callback attached to TAP device."""
            try:
                callback_count[0] += 1

                if callback_count[0] <= 10 or callback_count[0] % 100 == 0:
                    print(f"  🎵 TAP IOProc callback #{callback_count[0]} (device={device_id})")

                if input_data is None:
                    return 0

                num_buffers = input_data.mNumberBuffers
                if num_buffers == 0:
                    return 0

                buffer = input_data.mBuffers[0]
                if buffer.mData is None or buffer.mDataByteSize == 0:
                    return 0

                audio_data = bytes(buffer.mData[:buffer.mDataByteSize])

                try:
                    audio_queue.put_nowait(audio_data)
                except queue.Full:
                    pass

                return 0
            except Exception as e:
                print(f"  ❌ Callback error: {e}")
                return -1

        status, io_proc_id = AudioDeviceCreateIOProcID(
            tap_device_id,  # Attach to TAP device!
            tap_io_proc_callback,
            None,
            None
        )

        if status != 0:
            print(f"❌ AudioDeviceCreateIOProcID failed: status={status}")
            return 1

        print(f"✓ IOProc registered: {io_proc_id}")
        print()

        # Step 4: Start TAP device
        print("4. Starting TAP device...")
        status = AudioDeviceStart(tap_device_id, io_proc_id)

        if status != 0:
            print(f"❌ AudioDeviceStart failed: status={status}")
            return 1

        print(f"✓ TAP device started")
        print()

        # Step 5: Capture
        print("5. Capturing for 5 seconds...")
        print("   (Watch for callback messages)")
        print()

        time.sleep(5)

        print()
        print("6. Reading captured data...")
        chunk_count = 0
        total_bytes = 0

        while not audio_queue.empty():
            try:
                chunk = audio_queue.get_nowait()
                chunk_count += 1
                total_bytes += len(chunk)
            except queue.Empty:
                break

        print(f"✓ Chunks: {chunk_count}")
        print(f"✓ Total bytes: {total_bytes:,}")
        print()

        # Cleanup
        print("7. Cleaning up...")
        AudioDeviceStop(tap_device_id, io_proc_id)
        AudioDeviceDestroyIOProcID(tap_device_id, io_proc_id)

        print()
        print('='*70)

        if total_bytes > 0:
            print("✅ SUCCESS: Direct TAP device IOProc works!")
            print()
            print("This means:")
            print("  • The problem is with the Aggregate device setup")
            print("  • IOProc itself works fine when attached to TAP")
            print("  • Need to fix Aggregate device configuration")
        else:
            print("❌ FAILED: No audio even with direct TAP device")
            print()
            print("This means:")
            print("  • Problem is deeper than Aggregate device")
            print("  • IOProc may not work on TAP devices at all")
            print("  • Or TAP device needs additional configuration")

        return 0 if total_bytes > 0 else 1

    except Exception as e:
        print(f'\n❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
