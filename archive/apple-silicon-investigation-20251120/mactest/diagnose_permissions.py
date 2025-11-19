#!/usr/bin/env python3.12
"""Diagnose microphone and audio capture permissions in detail."""

import sys
import subprocess
import os

sys.path.insert(0, 'src')

def check_avfoundation_permission():
    """Check AVFoundation microphone permission."""
    print("1️⃣ AVFoundation Microphone Permission")
    print("─" * 70)
    try:
        from AVFoundation import AVCaptureDevice, AVMediaTypeAudio
        device = AVCaptureDevice.defaultDeviceWithMediaType_(AVMediaTypeAudio)
        if device:
            print(f"✅ AVFoundation can access microphone")
            print(f"   Device: {device}")
            return True
        else:
            print("❌ AVFoundation cannot access microphone (no device)")
            return False
    except Exception as e:
        print(f"❌ AVFoundation error: {e}")
        return False

def check_coreaudio_permission():
    """Check Core Audio property access permission."""
    print("\n2️⃣ Core Audio Property Access Permission")
    print("─" * 70)
    try:
        from proctap.backends.macos_coreaudio_ctypes import check_audio_capture_permission
        has_perm, msg = check_audio_capture_permission()
        if has_perm:
            print(f"✅ Core Audio property access: {msg}")
            return True
        else:
            print(f"❌ Core Audio property access denied: {msg}")
            return False
    except Exception as e:
        print(f"❌ Core Audio check error: {e}")
        return False

def check_system_settings_apps():
    """Show which apps should appear in System Settings."""
    print("\n3️⃣ Expected Apps in System Settings")
    print("─" * 70)

    print(f"Python executable: {sys.executable}")
    print(f"Process name: {os.path.basename(sys.executable)}")

    # Check parent process
    try:
        result = subprocess.run(
            ['ps', '-p', str(os.getppid()), '-o', 'comm='],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            parent = result.stdout.strip()
            print(f"Parent process: {parent}")
    except:
        pass

    print("\nIn System Settings → Privacy & Security → Microphone, look for:")
    print("  • python3.12")
    print("  • Python")
    print("  • Terminal (if running from Terminal.app)")
    print("  • iTerm2 (if running from iTerm2)")
    print("  • Your IDE (VS Code, PyCharm, etc.)")

def suggest_next_steps(av_perm, ca_perm):
    """Suggest next steps based on permission status."""
    print("\n4️⃣ Diagnosis & Next Steps")
    print("=" * 70)

    if av_perm and ca_perm:
        print("✅ All permissions granted! You should be able to capture audio.")
        print("\nNext: Run the test:")
        print("  ./quick_test.sh")
    elif av_perm and not ca_perm:
        print("⚠️  Interesting situation:")
        print("   • AVFoundation has microphone access ✓")
        print("   • Core Audio Process Tap API is denied ✗")
        print()
        print("This suggests Process Tap API might need separate permission.")
        print()
        print("📝 Steps to resolve:")
        print()
        print("1. Open System Settings manually:")
        print("   System Settings → Privacy & Security → Microphone")
        print()
        print("2. Check if your app (python3.12/Python/Terminal) is listed:")
        print("   • If listed: Enable the checkbox ✓")
        print("   • If not listed: The app hasn't requested permission yet")
        print()
        print("3. If not listed, try triggering via Process Tap directly:")
        print("   (This might show a different permission dialog)")
        print()
        print("4. Alternative: Run with sudo (not recommended for production):")
        print("   sudo python3.12 examples/macos_pyobjc_capture_test.py --pid <PID>")
        print()
        print("5. Check Console.app for TCC denial messages:")
        print("   Open Console.app → Search for 'TCC' or 'microphone'")
    elif not av_perm and not ca_perm:
        print("❌ No permissions granted.")
        print()
        print("📝 Steps to resolve:")
        print()
        print("1. Reset all microphone permissions:")
        print("   tccutil reset Microphone")
        print()
        print("2. Trigger permission dialog:")
        print("   python3.12 -c \"from AVFoundation import AVCaptureDevice, AVMediaTypeAudio; AVCaptureDevice.defaultDeviceWithMediaType_(AVMediaTypeAudio)\"")
        print()
        print("3. Click 'OK' when dialog appears")
        print()
        print("4. Check System Settings:")
        print("   System Settings → Privacy & Security → Microphone")
        print("   Enable checkbox for python3.12/Python/Terminal")
    elif not av_perm and ca_perm:
        print("⚠️  Unusual: Core Audio has access but AVFoundation doesn't")
        print()
        print("Try granting AVFoundation permission first, then test again.")

def main():
    """Main diagnostic function."""
    print()
    print("🔍 Microphone Permission Diagnostics")
    print("=" * 70)
    print()

    av_perm = check_avfoundation_permission()
    ca_perm = check_coreaudio_permission()
    check_system_settings_apps()
    suggest_next_steps(av_perm, ca_perm)

    print()
    print("=" * 70)
    print()

if __name__ == '__main__':
    main()
