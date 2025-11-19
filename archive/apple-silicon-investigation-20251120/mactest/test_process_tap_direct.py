#!/usr/bin/env python3.12
"""Test Process Tap creation directly to check actual TCC requirements."""

import sys
import subprocess

sys.path.insert(0, 'src')

def test_process_tap_creation():
    """Test if we can actually create a Process Tap."""
    print("🧪 Testing Process Tap Creation")
    print("=" * 70)
    print()

    # Get a PID to test with
    print("Finding a process with audio...")
    result = subprocess.run(['pgrep', '-f', 'say'], capture_output=True, text=True)

    if result.returncode != 0 or not result.stdout.strip():
        print("Starting a test audio process...")
        proc = subprocess.Popen(
            ['say', 'This is a test'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        test_pid = proc.pid
        print(f"✓ Started say process: PID {test_pid}")
    else:
        test_pid = int(result.stdout.strip().split()[0])
        print(f"✓ Found existing say process: PID {test_pid}")

    print()
    print(f"Attempting to create Process Tap for PID {test_pid}...")
    print()

    try:
        import objc
        from proctap.backends.macos_pyobjc import ProcessAudioDiscovery
        from CoreAudio import AudioHardwareCreateProcessTap
        from Foundation import NSArray, NSNumber, NSUUID
        import uuid

        # Step 1: Find process audio object
        print("Step 1: Finding process audio object...")
        discovery = ProcessAudioDiscovery()
        process_object_id = discovery.get_process_object_id(test_pid)

        if process_object_id is None:
            print(f"❌ Could not find audio object for PID {test_pid}")
            print("   This process might not be playing audio yet.")
            return False

        print(f"✓ Found process audio object: ID {process_object_id}")
        print()

        # Step 2: Create CATapDescription
        print("Step 2: Creating CATapDescription...")
        CATapDescription = objc.lookUpClass('CATapDescription')

        # Create NSArray with AudioObjectID
        process_array = NSArray.arrayWithObject_(
            NSNumber.numberWithUnsignedInt_(process_object_id)
        )

        # Create stereo mixdown tap
        tap_desc = CATapDescription.alloc().initStereoMixdownOfProcesses_(process_array)

        # Generate UUID
        tap_uuid = str(uuid.uuid4())
        tap_desc.setUUID_(NSUUID.alloc().initWithUUIDString_(tap_uuid))

        print(f"✓ Created CATapDescription with UUID: {tap_uuid}")
        print()

        # Step 3: Create Process Tap
        print("Step 3: Creating Process Tap...")
        print("   (This is where TCC permission might be required)")
        print()

        status, tap_device_id = AudioHardwareCreateProcessTap(tap_desc, None)

        if status == 0 and tap_device_id != 0:
            print(f"✅ SUCCESS! Process Tap created: Device ID {tap_device_id}")
            print()
            print("This means:")
            print("  • Process Tap API has the required permissions ✓")
            print("  • No additional TCC dialog is needed for Process Tap")
            print("  • The earlier status 2003332927 was from a different API")
            print()
            print("The actual issue might be with AudioObjectGetPropertyData")
            print("for certain properties, not with Process Tap itself.")
            print()

            # Clean up
            from CoreAudio import AudioHardwareDestroyAggregateDevice
            try:
                AudioHardwareDestroyAggregateDevice(tap_device_id)
                print("✓ Cleaned up Process Tap")
            except:
                pass

            return True
        else:
            print(f"❌ Failed to create Process Tap")
            print(f"   Status: {status}")
            print(f"   Device ID: {tap_device_id}")
            print()

            if status == 2003332927:  # 'wat?'
                print("Error 2003332927 ('wat?') = TCC permission denied")
                print()
                print("This means Process Tap API actually DOES need")
                print("microphone permission that hasn't been granted yet.")
                print()
                print("Solutions:")
                print("1. Check System Settings → Privacy & Security → Microphone")
                print("2. Enable checkbox for python3.12/Python/Terminal")
                print("3. Or try: tccutil reset Microphone && run test again")
            else:
                print(f"Unknown error code: {status}")

            return False

    except Exception as e:
        print(f"❌ Exception during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    print()
    success = test_process_tap_creation()
    print()
    print("=" * 70)

    if success:
        print()
        print("🎉 Process Tap works! You can proceed with audio capture.")
        print()
        print("Next steps:")
        print("  ./quick_test.sh")
        print()
    else:
        print()
        print("⚠️  Process Tap creation failed.")
        print()
        print("Please grant microphone permission:")
        print("1. Open System Settings")
        print("2. Go to Privacy & Security → Microphone")
        print("3. Enable python3.12/Python/Terminal")
        print("4. Run this test again")
        print()

if __name__ == '__main__':
    main()
