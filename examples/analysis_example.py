"""
Example: Real-time audio analysis and visualization

This example demonstrates how to use the audio analysis module to visualize
audio from a specific process.

Usage:
    # CLI mode (terminal-based)
    python examples/analysis_example.py --pid 12345

    # GUI mode (matplotlib window)
    python examples/analysis_example.py --pid 12345 --gui

    # Use process name
    python examples/analysis_example.py --name "VRChat.exe" --gui

Note:
    This is a simple wrapper around proctap.contrib.analysis main function.
    You can also run the analysis module directly:

    python -m proctap.contrib.analysis --pid 12345 --gui
"""

import sys
from proctap.contrib.analysis import main

if __name__ == "__main__":
    sys.exit(main())
