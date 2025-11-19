#!/bin/bash
# Quick test script for macOS audio capture with TCC permission handling

set -e

echo "🎤 ProcTap macOS Audio Capture Test"
echo "===================================="
echo ""

# Check if we're on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "❌ Error: This script is for macOS only"
    exit 1
fi

# Check Python version
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Error: python3.12 not found"
    echo "Please install Python 3.12 or modify this script to use your Python version"
    exit 1
fi

# Check PyObjC
echo "Checking dependencies..."
python3.12 -c "import CoreAudio" 2>/dev/null || {
    echo "❌ PyObjC not installed"
    echo "Installing PyObjC..."
    pip install pyobjc-core pyobjc-framework-CoreAudio
}

echo "✅ Dependencies OK"
echo ""

# Start a test audio process
echo "Starting test audio process..."
echo "This will use the 'say' command to generate audio"
echo ""

# Use a longer message so it plays for a while
say "Testing audio capture. This is a continuous audio stream for testing the process tap implementation. One two three four five six seven eight nine ten." &
SAY_PID=$!

echo "✅ Audio process started: PID $SAY_PID"
echo ""

# Give it a moment to start
sleep 1

# Run the capture test
echo "Running capture test (5 seconds)..."
echo ""
python3.12 examples/macos_pyobjc_capture_test.py --pid $SAY_PID --duration 5 --output test_output.wav

EXIT_CODE=$?

# Cleanup
echo ""
echo "Cleaning up..."
kill $SAY_PID 2>/dev/null || true
wait $SAY_PID 2>/dev/null || true

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Test completed successfully!"

    if [ -f "test_output.wav" ]; then
        echo ""
        echo "Audio saved to: test_output.wav"
        echo "File size: $(du -h test_output.wav | cut -f1)"
        echo ""
        echo "You can play it with:"
        echo "  afplay test_output.wav"
    fi
else
    echo ""
    echo "❌ Test failed (exit code: $EXIT_CODE)"
    echo ""
    echo "Common issues:"
    echo "  1. Microphone permission not granted"
    echo "     → Go to System Settings → Privacy & Security → Microphone"
    echo "     → Enable the checkbox for Terminal/Python"
    echo "     → Run this script again"
    echo ""
    echo "  2. macOS version too old (requires 14.4+)"
    echo "     → Check: sw_vers"
    echo ""
    echo "  3. Process not playing audio"
    echo "     → Make sure the target process is actively playing audio"
fi

exit $EXIT_CODE
