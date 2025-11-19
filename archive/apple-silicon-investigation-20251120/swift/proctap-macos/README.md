# proctap-macos

Swift CLI helper for ProcTap macOS backend.

This helper binary uses Core Audio Process Tap API (macOS 14.4+) to capture audio from specific processes and stream it as raw PCM to stdout.

## Requirements

- macOS 14.4 (Sonoma) or later
- Xcode 15.0 or later
- Swift 5.9 or later

## Building

### Using SwiftPM (Command Line)

```bash
cd swift/proctap-macos
swift build -c release
```

The binary will be located at `.build/release/proctap-macos`.

### Using Xcode

```bash
cd swift/proctap-macos
open Package.swift
```

Then build the `proctap-macos` target in Xcode.

## Usage

```bash
proctap-macos --pid <PID> [--sample-rate <rate>] [--channels <num>]
```

### Arguments

- `--pid <PID>`: Process ID to capture audio from (required)
- `--sample-rate <rate>`: Sample rate in Hz (default: 48000)
- `--channels <num>`: Number of channels (default: 2 for stereo)

### Example

```bash
# Capture audio from Safari (PID 1234)
proctap-macos --pid 1234 --sample-rate 48000 --channels 2 > output.raw

# Play captured audio with ffplay
ffplay -f s16le -ar 48000 -ac 2 output.raw
```

## Output Format

The helper outputs raw PCM audio to stdout in the following format:

- **Sample Format**: 16-bit signed little-endian (s16le)
- **Sample Rate**: Specified by `--sample-rate` (default 48000 Hz)
- **Channels**: Specified by `--channels` (default 2 for stereo)
- **Byte Order**: Little-endian

## Installation

For integration with Python package:

```bash
# Build release binary
swift build -c release

# Copy to Python package
cp .build/release/proctap-macos ../../src/proctap/bin/
```

## Permissions

The helper requires the following permissions:

- **Audio Capture**: `NSAudioCaptureUsageDescription`
- **Microphone** (implicit): `NSMicrophoneUsageDescription`

These are configured in `Info.plist`.

When first run, macOS will prompt the user to grant audio capture permission.

## Code Signing

For distribution, the binary should be code-signed:

```bash
codesign --sign "Developer ID Application: YOUR NAME" \
         --timestamp \
         --options runtime \
         .build/release/proctap-macos
```

For local development, ad-hoc signing is sufficient:

```bash
codesign --sign - .build/release/proctap-macos
```

## Architecture

```
┌─────────────────────┐
│  Python Backend     │
│  (macos.py)         │
└──────────┬──────────┘
           │ spawn subprocess
           ▼
┌─────────────────────┐
│  proctap-macos      │
│  (Swift CLI)        │
└──────────┬──────────┘
           │ Core Audio APIs
           ▼
┌─────────────────────┐
│  Process Tap API    │
│  (macOS 14.4+)      │
└──────────┬──────────┘
           │ capture
           ▼
┌─────────────────────┐
│  Target Process     │
│  Audio Output       │
└─────────────────────┘
```

## Core Audio APIs Used

- `kAudioHardwarePropertyTranslatePIDToProcessObject`: Convert PID to Audio Object ID
- `AudioHardwareCreateProcessTap`: Create process-specific audio tap
- `CATapDescription`: Configure tap with target process
- `AudioHardwareCreateAggregateDevice`: Create aggregate device for tap
- `AudioDeviceCreateIOProcID`: Set up audio callback
- `AudioDeviceStart`: Begin audio capture

## Troubleshooting

### "Operation not permitted"

Ensure the binary is code-signed and has the necessary entitlements.

### "Process tap creation failed"

- Verify target process is actively playing audio
- Check that macOS version is 14.4 or later
- Ensure audio capture permission is granted

### No audio output

- Verify target process PID is correct
- Check that the process has audio output
- Try increasing buffer size

## License

MIT License - See main project LICENSE file.
