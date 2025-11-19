#!/bin/bash
# Full audio capture test script

set -e

echo "🎤 Starting Audio Capture Test"
echo "==============================="
echo ""

# Start audio playback
echo "Starting audio playback..."
say "これは完全なオーディオキャプチャシステムのテストです。1から10まで数えます。1, 2, 3, 4, 5, 6, 7, 8, 9, 10。もう一度数えます。1, 2, 3, 4, 5, 6, 7, 8, 9, 10。3回目です。1, 2, 3, 4, 5, 6, 7, 8, 9, 10。" > /dev/null 2>&1 &
PID=$!

echo "✓ Audio process started: PID $PID"
echo ""

# Wait a moment for audio to start
sleep 1

# Run capture test
echo "Running capture test (6 seconds)..."
echo ""
python3.12 examples/macos_pyobjc_capture_test.py --pid $PID --duration 6 --output test_final.wav

EXIT_CODE=$?

# Clean up
kill $PID 2>/dev/null || true
wait $PID 2>/dev/null || true

echo ""
echo "==============================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test PASSED!"
    echo ""
    echo "Captured audio saved to: test_final.wav"

    if [ -f "test_final.wav" ]; then
        SIZE=$(du -h test_final.wav | cut -f1)
        echo "File size: $SIZE"
        echo ""
        echo "Play it with: afplay test_final.wav"
    fi
else
    echo "❌ Test FAILED (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
