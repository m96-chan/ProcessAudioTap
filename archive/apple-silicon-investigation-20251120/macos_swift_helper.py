"""
macOS Swift CLI Helper Backend for Process Tap API.

This backend uses a Swift CLI helper binary to capture per-process audio on macOS 14.4+.
The Swift helper implements Core Audio Process Tap API with block-based IOProc callbacks,
which are not properly supported in PyObjC.

Architecture:
- Swift binary: Independent executable with proper TCC permissions
- Python wrapper: Manages subprocess and reads PCM data from stdout
- Communication: Raw PCM audio streamed via stdout

This approach follows the AudioCap architecture and solves:
1. PyObjC block callback limitations
2. TCC permission issues with Python extensions
3. Provides proven, stable implementation

Requires:
- macOS 14.4+ (Sonoma)
- Swift helper binary (built from swift/proctap-helper)
- Microphone permission (TCC prompt will appear)
"""

from __future__ import annotations

import subprocess
import threading
import queue
import logging
import sys
from pathlib import Path
from typing import Callable, Optional

from .base import AudioBackend

logger = logging.getLogger(__name__)


def find_swift_helper() -> Optional[Path]:
    """
    Find the Swift CLI helper binary.

    Search order:
    1. Bundled binary (src/proctap/bin/proctap-helper)
    2. Development build (swift/proctap-helper/.build/*/release/proctap-helper)
    3. System PATH

    Returns:
        Path to Swift helper binary, or None if not found
    """
    # 1. Check bundled binary (installed package)
    import proctap
    package_dir = Path(proctap.__file__).parent
    bundled = package_dir / "bin" / "proctap-helper"
    if bundled.exists() and bundled.is_file():
        logger.debug(f"Found bundled Swift helper: {bundled}")
        return bundled

    # 2. Check development build
    repo_root = Path(__file__).parent.parent.parent.parent
    swift_dir = repo_root / "swift" / "proctap-helper" / ".build"
    if swift_dir.exists():
        # Find any architecture build
        for arch_dir in swift_dir.glob("*"):
            release_bin = arch_dir / "release" / "proctap-helper"
            if release_bin.exists() and release_bin.is_file():
                logger.debug(f"Found development Swift helper: {release_bin}")
                return release_bin

    # 3. Check PATH
    import shutil
    path_bin = shutil.which("proctap-helper")
    if path_bin:
        logger.debug(f"Found Swift helper in PATH: {path_bin}")
        return Path(path_bin)

    return None


def is_available() -> bool:
    """
    Check if Swift helper backend is available.

    Returns:
        True if macOS 14.4+ and Swift helper binary exists
    """
    import platform

    if platform.system() != "Darwin":
        return False

    # Check macOS version (14.4+)
    mac_ver = platform.mac_ver()[0]
    try:
        major, minor = map(int, mac_ver.split('.')[:2])
        if major < 14 or (major == 14 and minor < 4):
            logger.warning(f"macOS {mac_ver} detected. Process Tap API requires macOS 14.4+")
            return False
    except (ValueError, IndexError):
        logger.warning(f"Could not parse macOS version: {mac_ver}")
        return False

    # Check if Swift helper exists
    helper_path = find_swift_helper()
    if helper_path is None:
        logger.warning(
            "Swift helper binary not found. Build with:\n"
            "  cd swift/proctap-helper && swift build -c release"
        )
        return False

    return True


class SwiftHelperBackend(AudioBackend):
    """
    Swift CLI helper backend for macOS Process Tap API.

    This backend launches a Swift binary that captures audio from a specific
    process using Core Audio Process Tap API. Audio data is streamed as raw
    PCM via stdout.

    Audio Format:
    - Sample rate: Configurable (default 44100 Hz)
    - Channels: Configurable (default 2 - stereo)
    - Bit depth: 16-bit (fixed, determined by sample_width parameter)
    - Format: PCM signed integer

    Args:
        pid: Process ID to capture audio from
        sample_rate: Sample rate in Hz (default: 44100)
        channels: Number of channels (default: 2)
        sample_width: Bytes per sample (default: 2 for 16-bit)
    """

    def __init__(
        self,
        pid: int,
        sample_rate: int = 44100,
        channels: int = 2,
        sample_width: int = 2,
    ):
        super().__init__(pid)

        # Store format parameters
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width

        # Find Swift helper binary
        self._helper_path = find_swift_helper()
        if self._helper_path is None:
            raise RuntimeError(
                "Swift helper binary not found. Build with:\n"
                "  cd swift/proctap-helper && swift build -c release"
            )

        # Subprocess management
        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._should_stop = threading.Event()
        self._audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=100)

        # Callback
        self._callback: Optional[Callable[[bytes, int], None]] = None

        logger.info(
            f"SwiftHelperBackend initialized for PID {pid} "
            f"({sample_rate}Hz, {channels}ch, {sample_width*8}-bit)"
        )

    def start(self, callback: Optional[Callable[[bytes, int], None]] = None) -> None:
        """
        Start capturing audio from the target process.

        Args:
            callback: Optional callback function(chunk: bytes, frame_count: int)
                     Called for each audio chunk. If None, use read() or iter_chunks().

        Raises:
            RuntimeError: If capture fails to start
        """
        if self._process is not None:
            logger.warning("Swift helper already running")
            return

        self._callback = callback
        self._should_stop.clear()

        # Launch Swift helper subprocess
        cmd = [str(self._helper_path), str(self.pid)]
        logger.info(f"Launching Swift helper: {' '.join(cmd)}")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,  # Unbuffered
            )
        except Exception as e:
            raise RuntimeError(f"Failed to launch Swift helper: {e}") from e

        # Start reader thread
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            name=f"SwiftHelper-PID{self.pid}",
            daemon=True,
        )
        self._reader_thread.start()

        # Wait for "Ready" message on stderr
        try:
            stderr_line = self._process.stderr.readline().decode('utf-8', errors='replace')
            logger.debug(f"Swift helper stderr: {stderr_line.strip()}")
        except Exception as e:
            logger.warning(f"Could not read Swift helper stderr: {e}")

        logger.info("Swift helper capture started")

    def stop(self) -> None:
        """Stop capturing audio and clean up resources."""
        if self._process is None:
            return

        logger.info("Stopping Swift helper...")

        # Signal reader thread to stop
        self._should_stop.set()

        # Terminate subprocess
        if self._process.poll() is None:  # Still running
            self._process.terminate()
            try:
                self._process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                logger.warning("Swift helper did not terminate, killing...")
                self._process.kill()
                self._process.wait()

        # Wait for reader thread
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2.0)

        # Clean up
        self._process = None
        self._reader_thread = None
        self._callback = None

        logger.info("Swift helper stopped")

    def read(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Read one audio chunk (blocking).

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            Audio data as bytes, or None if timeout or stopped
        """
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_format(self) -> dict[str, int]:
        """
        Get audio format information.

        Returns:
            Dictionary with audio format details
        """
        return {
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'bits_per_sample': self.sample_width * 8,
            'sample_width': self.sample_width,
        }

    def _reader_loop(self) -> None:
        """
        Reader thread that reads PCM data from Swift helper stdout.

        Reads audio chunks and either:
        1. Calls user callback (if provided)
        2. Puts chunks in queue for read() or iter_chunks()
        """
        if self._process is None or self._process.stdout is None:
            logger.error("Cannot start reader loop: process not running")
            return

        # Calculate chunk size based on format
        # Read ~10ms chunks for low latency
        chunk_duration_ms = 10
        frame_size = self.channels * self.sample_width
        frames_per_chunk = (self.sample_rate * chunk_duration_ms) // 1000
        chunk_size = frames_per_chunk * frame_size

        logger.debug(f"Reader loop: chunk_size={chunk_size} bytes ({chunk_duration_ms}ms)")

        try:
            while not self._should_stop.is_set():
                # Read chunk from stdout
                chunk = self._process.stdout.read(chunk_size)

                if not chunk:  # EOF or process ended
                    logger.info("Swift helper stdout closed")
                    break

                # Calculate frame count
                frame_count = len(chunk) // frame_size

                # Deliver to callback or queue
                if self._callback:
                    try:
                        self._callback(chunk, frame_count)
                    except Exception as e:
                        logger.error(f"Callback error: {e}", exc_info=True)
                else:
                    try:
                        self._audio_queue.put(chunk, timeout=0.1)
                    except queue.Full:
                        logger.warning("Audio queue full, dropping chunk")

        except Exception as e:
            logger.error(f"Reader loop error: {e}", exc_info=True)

        finally:
            logger.debug("Reader loop exited")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup."""
        self.stop()
        return False

    def __repr__(self) -> str:
        return (
            f"SwiftHelperBackend(pid={self.pid}, "
            f"sample_rate={self.sample_rate}, "
            f"channels={self.channels}, "
            f"sample_width={self.sample_width})"
        )
