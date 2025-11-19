#!/bin/bash
# Test script for aggregate device

# Start 'say' command in background
say 'Testing audio capture for five seconds' &
SAY_PID=$!

echo "Started 'say' command with PID: $SAY_PID"
sleep 0.5

# Run test
python3.12 test_aggregate_device.py "$SAY_PID"

# Cleanup
wait "$SAY_PID" 2>/dev/null || true
