#!/usr/bin/env python3.12
"""Check TCC microphone permission status in detail."""

import subprocess
import sys
import os

def check_tcc_database():
    """Check the TCC database for microphone permissions."""
    print("🔍 Checking TCC Microphone Permissions")
    print("=" * 70)
    print()

    # Find the TCC database
    tcc_db_paths = [
        os.path.expanduser("~/Library/Application Support/com.apple.TCC/TCC.db"),
        "/Library/Application Support/com.apple.TCC/TCC.db"
    ]

    print("TCC Database Locations:")
    for path in tcc_db_paths:
        exists = "✓ EXISTS" if os.path.exists(path) else "✗ NOT FOUND"
        print(f"  {path}")
        print(f"    Status: {exists}")
    print()

    # Check using tccutil
    print("Using tccutil to check microphone status...")
    print()

    try:
        # Try to list microphone permissions (macOS 14+)
        result = subprocess.run(
            ['tccutil', 'list', 'Microphone'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout:
            print("📋 Apps with Microphone Access:")
            print(result.stdout)
        else:
            print("⚠️  tccutil list not supported or no output")
            if result.stderr:
                print(f"Error: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("⚠️  tccutil command timed out")
    except FileNotFoundError:
        print("⚠️  tccutil command not found")
    except Exception as e:
        print(f"⚠️  Error running tccutil: {e}")

    print()
    print("=" * 70)
    print()

def get_current_executable_info():
    """Get information about the current Python executable."""
    print("🐍 Current Python Executable Info")
    print("=" * 70)
    print()

    executable = sys.executable
    print(f"Executable: {executable}")
    print(f"Version: {sys.version}")

    # Check if it's a symlink
    if os.path.islink(executable):
        real_path = os.path.realpath(executable)
        print(f"Real path: {real_path}")

    # Get the app bundle if running from one
    try:
        result = subprocess.run(
            ['ps', '-p', str(os.getpid()), '-o', 'comm='],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"Process name: {result.stdout.strip()}")
    except:
        pass

    print()
    print("=" * 70)
    print()

def suggest_solutions():
    """Suggest solutions for granting microphone permission."""
    print("💡 How to Grant Microphone Permission")
    print("=" * 70)
    print()

    print("Method 1: Use System Settings (Recommended)")
    print("─" * 70)
    print("1. Open System Settings")
    print("2. Go to 'Privacy & Security' → 'Microphone'")
    print("3. Look for one of these:")
    print("   • Terminal (if running from Terminal.app)")
    print("   • iTerm2 (if running from iTerm2)")
    print("   • Python or python3.12")
    print("   • Your IDE name (VS Code, PyCharm, etc.)")
    print()
    print("4. Enable the checkbox ✓")
    print()

    print("Method 2: Reset Microphone Permissions (if dialog won't appear)")
    print("─" * 70)
    print("Run this command in Terminal:")
    print()
    print("  tccutil reset Microphone")
    print()
    print("This will reset ALL microphone permissions.")
    print("The permission dialog will appear next time any app requests access.")
    print()

    print("Method 3: Use a Simple Audio Test")
    print("─" * 70)
    print("Sometimes the permission dialog only appears when actually accessing")
    print("the microphone. Try running this:")
    print()
    print("  python3.12 -c \"from AVFoundation import AVCaptureDevice, AVMediaTypeAudio; print(AVCaptureDevice.defaultDeviceWithMediaType_(AVMediaTypeAudio))\"")
    print()
    print("If a dialog appears, click 'OK' or 'Allow'.")
    print()

    print("Method 4: Check for Existing Denial")
    print("─" * 70)
    print("If you previously denied permission, you need to:")
    print("1. Find the app in System Settings → Privacy & Security → Microphone")
    print("2. Toggle it OFF then ON again")
    print("3. Or use 'tccutil reset Microphone' to clear the denial")
    print()

    print("=" * 70)
    print()

def main():
    """Main function."""
    print()

    get_current_executable_info()
    check_tcc_database()
    suggest_solutions()

    print("After granting permission, test with:")
    print("  ./quick_test.sh")
    print()
    print("Or:")
    print("  python3.12 examples/macos_pyobjc_capture_test.py --pid <PID> --duration 5")
    print()

if __name__ == '__main__':
    main()
