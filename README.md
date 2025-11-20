<div align="center">

# 📡 ProcTap

**Cross-Platform Per-Process Audio Capture**

[![PyPI version](https://img.shields.io/pypi/v/proc-tap?color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/proc-tap/)
[![Python versions](https://img.shields.io/pypi/pyversions/proc-tap?logo=python&logoColor=white)](https://pypi.org/project/proc-tap/)
[![Downloads](https://img.shields.io/pypi/dm/proc-tap?logo=pypi&logoColor=white)](https://pypi.org/project/proc-tap/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux*%20%7C%20macOS*-blue)](https://github.com/m96-chan/ProcTap)

[![Build wheels](https://github.com/m96-chan/ProcTap/actions/workflows/build-wheels.yml/badge.svg)](https://github.com/m96-chan/ProcTap/actions/workflows/build-wheels.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub stars](https://img.shields.io/github/stars/m96-chan/ProcTap?style=social)](https://github.com/m96-chan/ProcTap/stargazers)

---

ProcTap is a Python library for per-process audio capture with platform-specific backends.

**Capture audio from a specific process only** — without system sounds or other app audio mixed in.
Ideal for VRChat, games, DAWs, browsers, and AI audio analysis pipelines.

### Platform Support

| Platform | Status | Backend | Notes |
|----------|--------|---------|-------|
| **Windows** | ✅ **Fully Supported** | WASAPI (C++ native) | Windows 10/11 (20H1+) |
| **Linux** | ✅ **Fully Supported** | PipeWire Native / PulseAudio | Per-process isolation, auto-fallback (v0.3.0+) |
| **macOS** | ✅ **Officially Supported** | ScreenCaptureKit | macOS 13+ (Ventura), bundleID-based (v0.4.0+) |

<sub>\* Linux is fully supported with PipeWire/PulseAudio (v0.3.0+). macOS is officially supported with ScreenCaptureKit (v0.4.0+).</sub>

</div>

---

## 🚀 Features

- 🎧 **Capture audio from a single target process**
  (VRChat, games, browsers, Discord, DAWs, streaming tools, etc.)

- 🌍 **Cross-platform architecture**
  → Windows (fully supported) | Linux (fully supported, v0.3.0+) | macOS (officially supported, v0.4.0+)

- ⚡ **Platform-optimized backends**
  → Windows: ActivateAudioInterfaceAsync (modern WASAPI)
  → Linux: PipeWire Native API / PulseAudio (fully supported, v0.3.0+)
  → macOS: ScreenCaptureKit API (macOS 13+, bundleID-based, v0.4.0+)

- 🧵 **Low-latency, thread-safe audio engine**
  → 48 kHz / stereo / float32 format (Windows)

- 🐍 **Python-friendly high-level API**
  - Callback-based streaming
  - Async generator streaming (`async for`)

- 🔌 **Native extensions for high-performance**
  → C++ extension on Windows for optimal throughput

---

## 📦 Installation

**From PyPI**:

```bash
pip install proc-tap
```

**Platform-specific dependencies are automatically installed:**
- Windows: No additional dependencies
- Linux: `pulsectl` is automatically installed, but you also need system packages:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install pulseaudio-utils

  # Fedora/RHEL
  sudo dnf install pulseaudio-utils
  ```

**Optional: High-Quality Audio Resampling** (74% faster / 3.8x speedup for sample rate conversion):

```bash
pip install proc-tap[hq-resample]
```

**Performance:** With `libsamplerate`, resampling achieves **0.66ms per 10ms chunk** (vs 2.6ms with scipy-only).

**Compatibility Notes:**
- ✅ **Python 3.10-3.12**: Works on all platforms
- ✅ **Linux/macOS + Python 3.13+**: Should work (you can try it!)
- ⚠️ **Windows + Python 3.13+**: May fail to build (as of 2025-01)
  - If it fails, the library automatically falls back to scipy's polyphase filtering
  - Still provides excellent audio quality, just 74% slower for resampling
  - You can still try installing - if it works, great! If not, no harm done.

📚 **[Read the Full Documentation](https://m96-chan.github.io/ProcTap/)** for detailed guides and API reference.

**From TestPyPI** (for testing pre-releases):

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ proctap
```

**From Source**:

```bash
git clone https://github.com/m96-chan/ProcTap
cd ProcTap
pip install -e .
```

---

## 🎬 CLI Usage (Pipe to FFmpeg)

ProcTap includes a CLI for piping audio directly to FFmpeg or other tools:

```bash
# Pipe to FFmpeg (MP3 encoding) - Direct command
proctap --pid 12345 --stdout | ffmpeg -f s16le -ar 48000 -ac 2 -i pipe:0 output.mp3

# Or using python -m
python -m proctap --pid 12345 --stdout | ffmpeg -f s16le -ar 48000 -ac 2 -i pipe:0 output.mp3

# Using process name instead of PID
proctap --name "VRChat.exe" --stdout | ffmpeg -f s16le -ar 48000 -ac 2 -i pipe:0 output.mp3

# FLAC encoding (lossless)
proctap --pid 12345 --stdout | ffmpeg -f s16le -ar 48000 -ac 2 -i pipe:0 output.flac

# Native float32 output (no conversion)
proctap --pid 12345 --format float32 --stdout | ffmpeg -f f32le -ar 48000 -ac 2 -i pipe:0 output.mp3
```

**CLI Options:**

| Option | Description |
|--------|-------------|
| `--pid PID` | Process ID to capture (required if `--name` not used) |
| `--name NAME` | Process name to capture (e.g., `VRChat.exe` or `VRChat`) |
| `--stdout` | Output raw PCM to stdout for piping (required) |
| `--format {int16,float32}` | Output format: int16 or float32 (default: int16) |
| `--verbose` | Enable verbose logging to stderr |
| `--list-audio-procs` | List all processes currently playing audio |

**Finding Process IDs:**

```bash
# Windows
tasklist | findstr "VRChat"

# Linux/macOS
ps aux | grep VRChat
```

**FFmpeg Format Arguments:**

The CLI outputs raw PCM at 48kHz stereo. FFmpeg needs these arguments based on `--format`:

**int16 (default):**
- `-f s16le`: Signed 16-bit little-endian PCM
- `-ar 48000`: Sample rate (48kHz, fixed)
- `-ac 2`: Channels (stereo, fixed)
- `-i pipe:0`: Read from stdin

**float32:**
- `-f f32le`: 32-bit float little-endian PCM
- `-ar 48000`: Sample rate (48kHz, fixed)
- `-ac 2`: Channels (stereo, fixed)
- `-i pipe:0`: Read from stdin

---

## 🛠 Requirements

**Windows (Fully Supported):**
- Windows 10 / 11 (20H1 or later)
- Python 3.10+
- WASAPI support
- **No admin privileges required**

**Linux (Fully Supported - v0.3.0+):**
- Linux with PulseAudio or PipeWire
- Python 3.10+
- **Auto-detection:** Automatically selects best available backend
- **Native PipeWire API** (in development, experimental):
  - `libpipewire-0.3-dev`: `sudo apt-get install libpipewire-0.3-dev`
  - Target latency: ~2-5ms (when fully implemented)
  - Auto-selected when available (may fall back to subprocess)
- **PipeWire subprocess:**
  - `pw-record`: install with `sudo apt-get install pipewire-media-session`
- **PulseAudio fallback:**
  - `pulsectl` library: automatically installed
  - `parec` command: `sudo apt-get install pulseaudio-utils`
- ✅ **Per-process isolation** using null-sink strategy
- ✅ **Graceful fallback** chain: Native → PipeWire subprocess → PulseAudio

**macOS (Officially Supported - v0.4.0+):**
- macOS 13.0 (Ventura) or later (macOS 13+ recommended)
- Python 3.10+
- Swift helper binary (screencapture-audio)
- Screen Recording permission (automatically prompted)
- ✅ **ScreenCaptureKit Backend:** Apple Silicon compatible, no AMFI/SIP hacks needed
- ✅ **Simple Permissions:** Screen Recording only (no Microphone/TCC hacks)
- ✅ **Low Latency:** ~10-15ms audio capture

---

## 🧰 Basic Usage (Callback API)

```python
from proctap import ProcTap, StreamConfig

def on_chunk(pcm: bytes, frames: int):
    print(f"Received {len(pcm)} bytes ({frames} frames)")

pid = 12345  # Target process ID

tap = ProcTap(pid, StreamConfig(), on_data=on_chunk)
tap.start()

input("Recording... Press Enter to stop.\n")

tap.close()
```

---

## 🔁 Async Usage (Async Generator)

```python
import asyncio
from proctap import ProcTap

async def main():
    tap = ProcTap(pid=12345)
    tap.start()

    async for chunk in tap.iter_chunks():
        print(f"PCM chunk size: {len(chunk)} bytes")

asyncio.run(main())
```

---

## 📄 API Overview

### `class ProcTap`

**Control Methods:**

| Method | Description |
|--------|-------------|
| `start()` | Start WASAPI per-process capture |
| `stop()` | Stop capture |
| `close()` | Release native resources |

**Data Access:**

| Method | Description |
|--------|-------------|
| `iter_chunks()` | Async generator yielding PCM chunks |
| `read(timeout=1.0)` | Synchronous: read one chunk (blocking) |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `is_running` | bool | Check if capture is active |
| `pid` | int | Get target process ID |
| `config` | StreamConfig | Get stream configuration |

**Utility Methods:**

| Method | Description |
|--------|-------------|
| `set_callback(callback)` | Change or remove audio callback |
| `get_format()` | Get audio format info (dict) |

### Audio Format

**Windows Backend Format** (WASAPI, returned to Python):

| Parameter | Value | Description |
|-----------|-------|-------------|
| Sample Rate | **48,000 Hz** | Professional audio quality |
| Channels | **2** | Stereo |
| Format | **float32** | IEEE 754 floating point (-1.0 to +1.0) |
| Fallback | **44.1kHz int16** | Auto-converted to 48kHz float32 if float32 init fails |

**Important Note:** For WAV file output, you must convert float32 to int16:

```python
import numpy as np

def on_data(pcm: bytes, frames: int):
    # Convert float32 to int16 for WAV files
    float_samples = np.frombuffer(pcm, dtype=np.float32)
    int16_samples = (np.clip(float_samples, -1.0, 1.0) * 32767).astype(np.int16)
    wav.writeframes(int16_samples.tobytes())
```

---

## 🎯 Use Cases

- 🎮 Record audio from one game only
- 🕶 Capture VRChat audio cleanly (without system sounds)
- 🎙 Feed high-SNR audio into AI recognition models
- 📹 Alternative to OBS "Application Audio Capture"
- 🎧 Capture DAW/app playback for analysis tools

---

## 🎨 Advanced Features (Contrib)

ProcTap includes optional contrib modules for advanced audio processing:

### 📊 Real-Time Audio Analysis & Visualization

Monitor and analyze audio from processes in real-time with spectrum analysis, volume meters, and frequency visualization.

**CLI Mode** (Terminal-based):
```bash
# Analyze by process ID
python -m proctap.contrib.analysis --pid 12345

# Analyze by process name
python -m proctap.contrib.analysis --name "VRChat.exe"
```

**GUI Mode** (Matplotlib window):
```bash
# Launch GUI visualizer
python -m proctap.contrib.analysis --pid 12345 --gui

# Adjust FFT size for better frequency resolution
python -m proctap.contrib.analysis --pid 12345 --gui --fft-size 4096
```

**Features:**
- 📈 **Real-time spectrum analyzer** (FFT-based frequency analysis)
- 🔊 **Volume meters** (RMS and peak levels in dB)
- 🎵 **Frequency band analysis** (Sub, Bass, Mid, Treble, Presence, Brilliance)
- 💻 **Terminal visualization** (CLI mode) or 📊 **Matplotlib plots** (GUI mode)
- ⚙️ **Configurable FFT size** (512, 1024, 2048, 4096, 8192)

**Programmatic Usage:**
```python
from proctap import ProcessAudioCapture
from proctap.contrib import AudioAnalyzer, CLIVisualizer

# Create analyzer
analyzer = AudioAnalyzer(sample_rate=48000, fft_size=2048)

# Create callback for audio processing
def on_audio(pcm: bytes, frames: int):
    analyzer.process_audio(pcm)

# Start audio capture with callback
tap = ProcessAudioCapture(pid=12345, on_data=on_audio)
tap.start()

# Create and run visualizer
visualizer = CLIVisualizer(analyzer)
visualizer.start()  # Blocking - displays in terminal
```

**Optional Dependencies:**
- CLI mode: Included (uses numpy/scipy)
- GUI mode: Requires `matplotlib` (`pip install matplotlib`)

---

## 📚 Example: Save to WAV

```python
from proctap import ProcTap
import wave

pid = 12345

wav = wave.open("output.wav", "wb")
wav.setnchannels(2)
wav.setsampwidth(2)  # 16-bit PCM
wav.setframerate(44100)  # Native format is 44.1 kHz

def on_data(pcm, frames):
    wav.writeframes(pcm)

with ProcTap(pid, on_data=on_data):
    input("Recording... Press Enter to stop.\n")

wav.close()
```

---

## 📚 Example: Synchronous Read API

```python
from proctap import ProcTap

tap = ProcTap(pid=12345)
tap.start()

try:
    while True:
        chunk = tap.read(timeout=1.0)  # Blocking read
        if chunk:
            print(f"Got {len(chunk)} bytes")
            # Process audio data...
        else:
            print("Timeout, no data")
except KeyboardInterrupt:
    pass
finally:
    tap.close()
```

---

## 🐧 Linux Example

```python
from proctap import ProcessAudioCapture, StreamConfig
import wave

pid = 12345  # Your target process ID

# Create WAV file
wav = wave.open("linux_capture.wav", "wb")
wav.setnchannels(2)
wav.setsampwidth(2)
wav.setframerate(44100)

def on_data(pcm, frames):
    wav.writeframes(pcm)

# Create stream config (Linux backend respects these settings)
config = StreamConfig(sample_rate=44100, channels=2)

try:
    with ProcessAudioCapture(pid, config=config, on_data=on_data):
        print("⚠️  Make sure the process is actively playing audio!")
        input("Recording... Press Enter to stop.\n")
finally:
    wav.close()
```

**Linux-specific requirements:**
- Install system package: `sudo apt-get install pulseaudio-utils` (provides `parec` command)
- Python dependency `pulsectl` is automatically installed with `pip install proc-tap`
- The target process must be actively playing audio
- See [examples/linux_basic.py](examples/linux_basic.py) for a complete example

---

## 🍎 macOS Example (v0.4.0+)

```python
from proctap import ProcessAudioCapture, StreamConfig
import wave

pid = 12345  # Your target process ID

# Create WAV file
wav = wave.open("macos_capture.wav", "wb")
wav.setnchannels(2)
wav.setsampwidth(2)
wav.setframerate(48000)  # macOS backend default is 48 kHz

def on_data(pcm, frames):
    wav.writeframes(pcm)

# Create stream config (macOS backend respects these settings)
config = StreamConfig(sample_rate=48000, channels=2)

try:
    with ProcessAudioCapture(pid, config=config, on_data=on_data):
        print("⚠️  Make sure the process is actively playing audio!")
        print("⚠️  On first run, macOS will prompt for Screen Recording permission.")
        input("Recording... Press Enter to stop.\n")
finally:
    wav.close()
```

**macOS-specific requirements (v0.4.0+):**
- macOS 13.0 (Ventura) or later
- Swift helper binary (screencapture-audio) - automatically built during installation
- Screen Recording permission - macOS will prompt on first run
- The target process must be actively playing audio
- Works with bundleID-based capture (PID is automatically converted to bundleID)
- See [examples/macos_screencapture_test.py](examples/macos_screencapture_test.py) for a complete example

**Building the Swift helper manually:**
```bash
cd src/proctap/swift/screencapture-audio
swift build -c release
```

**Note:** The ScreenCaptureKit backend (v0.4.0+) is recommended over the experimental PyObjC/C extension backends.

---

## 🏗 Build From Source

```bash
git clone https://github.com/m96-chan/ProcTap
cd ProcTap
pip install -e .
```

**Windows Build Requirements:**
- Visual Studio Build Tools
- Windows SDK
- CMake (if you modularize the C++ code)

**Linux:**
- No C++ compiler required (pure Python)
- System dependencies: `pulseaudio-utils` or `pipewire` with `libpipewire-0.3-dev`

**macOS:**
- Swift toolchain required for building the ScreenCaptureKit helper (v0.4.0+)
- Xcode Command Line Tools: `xcode-select --install`
- No C++ compiler required (pure Python backend)
- Helper binary location: `src/proctap/swift/screencapture-audio/`

---

## 🤝 Contributing

Contributions are welcome! We have structured issue templates to help guide your contributions:

- 🐛 [**Bug Report**](../../issues/new?template=bug_report.yml) - Report bugs or unexpected behavior
- ✨ [**Feature Request**](../../issues/new?template=feature_request.yml) - Suggest new features or enhancements
- ⚡ [**Performance Issue**](../../issues/new?template=performance.yml) - Report performance problems or optimizations
- 🔧 [**Type Hints / Async**](../../issues/new?template=type_hints_async.yml) - Improve type annotations or async functionality
- 📚 [**Documentation**](../../issues/new?template=documentation.yml) - Improve docs, examples, or guides

**Special Interest:**
- PRs from WASAPI/C++ experts are especially appreciated
- **Linux backend improvements** (PulseAudio/PipeWire per-app isolation)
- **macOS backend testing** (ScreenCaptureKit on macOS 13+)
- Cross-platform testing and compatibility
- Performance profiling and optimization

---

## 📄 License

```
MIT License
```

---

## 👤 Author

**m96-chan**  
Windows Audio / VRChat Tools / Python / C++  
https://github.com/m96-chan

