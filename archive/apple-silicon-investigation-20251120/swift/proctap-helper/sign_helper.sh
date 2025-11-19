#!/bin/bash
# Code signing script for proctap-helper
# This script needs keychain access, so run it manually in Terminal

set -e

HELPER_PATH=".build/arm64-apple-macosx/release/proctap-helper.app/Contents/MacOS/proctap-helper"
ENTITLEMENTS="proctap-helper-debug.entitlements"
CERT_NAME="Apple Development: saxia.re@gmail.com (2ERJ27225X)"

echo "=== Code Signing proctap-helper ==="
echo ""

# Step 1: Ensure Xcode is active developer directory
echo "Step 1: Checking Xcode developer directory..."
CURRENT_DEV_DIR=$(xcode-select -p)
if [[ "$CURRENT_DEV_DIR" != "/Applications/Xcode.app/Contents/Developer" ]]; then
    echo "  Switching to Xcode.app..."
    sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
    echo "  ✓ Switched to Xcode.app"
else
    echo "  ✓ Already using Xcode.app"
fi
echo ""

# Step 2: Verify certificate exists
echo "Step 2: Checking for certificate..."
if security find-certificate -c "$CERT_NAME" ~/Library/Keychains/login.keychain-db > /dev/null 2>&1; then
    echo "  ✓ Certificate found"
else
    echo "  ✗ Certificate not found!"
    echo "  Please create Apple Development certificate in Xcode:"
    echo "    Xcode → Settings → Accounts → Manage Certificates → +"
    exit 1
fi
echo ""

# Step 3: Sign the binary
echo "Step 3: Signing binary..."
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
    echo "  You may need to unlock your keychain first:"
    echo "    security unlock-keychain ~/Library/Keychains/login.keychain-db"
    exit 1
fi
echo ""

# Step 4: Verify signature
echo "Step 4: Verifying signature..."
codesign -dv --entitlements - "$HELPER_PATH" 2>&1 | grep -E "(Identifier|Authority|Entitlements)"
echo ""

# Step 5: Test with say command
echo "Step 5: Testing signed binary..."
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
