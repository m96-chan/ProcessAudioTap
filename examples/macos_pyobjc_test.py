#!/usr/bin/env python3
"""
macOS PyObjC Core Audio prototype test script.

This script tests the PyObjC-based Core Audio integration for process audio discovery.

Phase 1 Testing:
- Process object ID translation (PID → AudioObjectID)
- Detection of processes with active audio output
- API availability checks

Usage:
    python examples/macos_pyobjc_test.py --pid 12345
    python examples/macos_pyobjc_test.py --name Music
    python examples/macos_pyobjc_test.py --list

Requirements:
- macOS 14.4+
- PyObjC: pip install pyobjc-core pyobjc-framework-CoreAudio
- psutil (for process listing): pip install psutil

Example:
    # Test with Music.app
    python examples/macos_pyobjc_test.py --name Music

    # Test with Safari
    python examples/macos_pyobjc_test.py --name Safari

    # List all processes with audio
    python examples/macos_pyobjc_test.py --list
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from proctap.backends import macos_pyobjc
except ImportError as e:
    print(f"ERROR: Failed to import macos_pyobjc module: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def find_pid_by_name(process_name: str) -> list[tuple[int, str]]:
    """
    Find PIDs by process name.

    Args:
        process_name: Process name to search for (case-insensitive)

    Returns:
        List of tuples (pid, full_name)

    Raises:
        RuntimeError: If psutil is not available
    """
    try:
        import psutil
    except ImportError:
        raise RuntimeError(
            "psutil is required for process name lookup. "
            "Install it with: pip install psutil"
        )

    matching_processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                matching_processes.append((proc.info['pid'], proc.info['name']))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return matching_processes


def list_processes_with_audio() -> None:
    """List all processes with active audio output."""
    try:
        import psutil
    except ImportError:
        print("ERROR: psutil is required for listing processes")
        print("Install with: pip install psutil")
        sys.exit(1)

    print("Scanning for processes with audio output...")
    print("=" * 60)

    discovery = macos_pyobjc.ProcessAudioDiscovery()
    found_count = 0

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            pid = proc.info['pid']
            name = proc.info['name']

            # Check if process has audio
            if discovery.find_process_with_audio(pid):
                object_id = discovery.get_process_object_id(pid)
                print(f"✓ PID {pid:6d}: {name:30s} (ObjectID: {object_id})")
                found_count += 1

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        except Exception as e:
            # Skip processes that cause errors
            pass

    print("=" * 60)
    print(f"Found {found_count} processes with active audio output")


def test_process_by_pid(pid: int) -> int:
    """
    Test process audio discovery by PID.

    Args:
        pid: Process ID to test

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print(f"Testing process audio discovery for PID {pid}")
    print("=" * 60)

    try:
        discovery = macos_pyobjc.ProcessAudioDiscovery()

        # Check if process has audio
        has_audio = discovery.find_process_with_audio(pid)

        if has_audio:
            object_id = discovery.get_process_object_id(pid)
            print(f"✓ Process {pid} has active audio output")
            print(f"  Core Audio ObjectID: {object_id}")
            print()
            print("Phase 1 Test: PASSED")
            return 0
        else:
            print(f"✗ Process {pid} does not have active audio output")
            print()
            print("Possible reasons:")
            print("  - Process is not currently playing audio")
            print("  - Process does not have audio output capabilities")
            print("  - Process ID does not exist")
            print()
            print("Phase 1 Test: FAILED (no audio detected)")
            return 1

    except Exception as e:
        print(f"✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("Phase 1 Test: FAILED (exception)")
        return 1


def test_process_by_name(process_name: str) -> int:
    """
    Test process audio discovery by name.

    Args:
        process_name: Process name to search for

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print(f"Searching for process: {process_name}")
    print("=" * 60)

    try:
        matching_processes = find_pid_by_name(process_name)

        if not matching_processes:
            print(f"✗ No process found with name containing '{process_name}'")
            return 1

        if len(matching_processes) > 1:
            print(f"Found {len(matching_processes)} matching processes:")
            for pid, name in matching_processes:
                print(f"  PID {pid:6d}: {name}")
            print()
            print(f"Using first match: PID {matching_processes[0][0]}")
            print()

        pid, full_name = matching_processes[0]
        print(f"Testing: {full_name} (PID {pid})")
        print()

        return test_process_by_pid(pid)

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test PyObjC Core Audio prototype for process audio discovery"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--pid',
        type=int,
        help='Process ID to test'
    )
    group.add_argument(
        '--name',
        type=str,
        help='Process name to search for (e.g., "Music", "Safari")'
    )
    group.add_argument(
        '--list',
        action='store_true',
        help='List all processes with active audio output'
    )

    args = parser.parse_args()

    # Check PyObjC availability
    if not macos_pyobjc.is_available():
        print("ERROR: PyObjC Core Audio bindings not available")
        print()
        print("Install with:")
        print("  pip install pyobjc-core pyobjc-framework-CoreAudio")
        return 1

    # Check macOS version
    if not macos_pyobjc.supports_process_tap():
        major, minor, patch = macos_pyobjc.get_macos_version()
        print(f"ERROR: macOS {major}.{minor}.{patch} does not support Process Tap API")
        print("Requires macOS 14.4 (Sonoma) or later")
        return 1

    major, minor, patch = macos_pyobjc.get_macos_version()
    print(f"macOS Version: {major}.{minor}.{patch}")
    print(f"PyObjC Status: Available ✓")
    print(f"Process Tap API: Supported ✓")
    print()

    # Run requested test
    if args.list:
        list_processes_with_audio()
        return 0
    elif args.pid:
        return test_process_by_pid(args.pid)
    elif args.name:
        return test_process_by_name(args.name)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
