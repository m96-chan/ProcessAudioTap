#!/bin/bash
# Code signing script for proctap-helper (no sudo required)

set -e

HELPER_PATH=".build/arm64-apple-macosx/release/proctap-helper.app/Contents/MacOS/proctap-helper"
ENTITLEMENTS="proctap-helper-debug.entitlements"
CERT_NAME="Apple Development: saxia.re@gmail.com (2ERJ27225X)"

echo "=== Code Signing proctap-helper ==="
echo ""

# Step 1: Verify certificate exists
echo "Step 1: Checking for certificate..."
if security find-certificate -c "$CERT_NAME" ~/Library/Keychains/login.keychain-db > /dev/null 2>&1; then
    echo "  ✓ Certificate found"
else
    echo "  ✗ Certificate not found!"
    exit 1
fi
echo ""

# Step 2: Sign the binary
echo "Step 2: Signing binary..."
codesign --force \
         --sign "$CERT_NAME" \
         --entitlements "$ENTITLEMENTS" \
         --options runtime \
         --timestamp \
         "$HELPER_PATH"

if [ $? -eq 0 ]; then
    echo "  ✓ Signing successful"
else
    echo "  ✗ Signing failed"
    exit 1
fi
echo ""

# Step 3: Verify signature
echo "Step 3: Verifying signature..."
codesign -dv --entitlements - "$HELPER_PATH" 2>&1 | grep -E "(Identifier|Authority|Entitlements)"
echo ""

# Step 4: Test with say command
echo "Step 4: Testing signed binary..."
say "Testing signed binary" &
sleep 0.5
SAY_PID=$(ps aux | grep " say " | grep -v grep | awk '{print $2}' | head -1)

if [ -n "$SAY_PID" ]; then
    echo "  Found 'say' process with PID: $SAY_PID"
    echo "  Running proctap-helper..."
    echo ""
    timeout 3 "$HELPER_PATH" "$SAY_PID" 2>&1 | head -50
else
    echo "  ✗ Could not find 'say' process"
fi

echo ""
echo "=== Done ==="
