#!/bin/bash
# Build ProcTap Helper as an application bundle with proper Info.plist

set -e

# Configuration
APP_NAME="proctap-helper"
BUNDLE_ID="com.proctap.helper"
BUILD_DIR=".build/arm64-apple-macosx/release"
APP_BUNDLE="${BUILD_DIR}/${APP_NAME}.app"
MACOS_DIR="${APP_BUNDLE}/Contents/MacOS"
RESOURCES_DIR="${APP_BUNDLE}/Contents/Resources"

echo "Building Swift executable..."
swift build -c release

echo "Creating application bundle structure..."
rm -rf "${APP_BUNDLE}"
mkdir -p "${MACOS_DIR}"
mkdir -p "${RESOURCES_DIR}"

echo "Copying executable..."
cp "${BUILD_DIR}/${APP_NAME}" "${MACOS_DIR}/"

echo "Creating Info.plist..."
cat > "${APP_BUNDLE}/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleExecutable</key>
	<string>proctap-helper</string>
	<key>CFBundleIdentifier</key>
	<string>com.proctap.helper</string>
	<key>CFBundleName</key>
	<string>ProcTap Helper</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleVersion</key>
	<string>1.0</string>
	<key>CFBundleShortVersionString</key>
	<string>1.0</string>
	<key>LSMinimumSystemVersion</key>
	<string>14.0</string>
	<key>LSUIElement</key>
	<true/>
	<key>NSMicrophoneUsageDescription</key>
	<string>ProcTap Helper needs microphone access to capture audio from specific processes using Core Audio Process Tap API.</string>
	<key>NSSystemAdministrationUsageDescription</key>
	<string>ProcTap Helper needs system access to monitor and capture audio from other processes.</string>
</dict>
</plist>
EOF

echo "Application bundle created: ${APP_BUNDLE}"
echo ""
echo "To run:"
echo "  ${APP_BUNDLE}/Contents/MacOS/${APP_NAME} <PID>"
echo ""
echo "Or create a wrapper script for convenience."
