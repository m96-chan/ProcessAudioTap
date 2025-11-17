"""
Linux audio capture backend.

This module provides process-specific audio capture on Linux using PulseAudio
or PipeWire (via PulseAudio compatibility layer).

STATUS: Experimental - PulseAudio support implemented
NOTE: Requires pulsectl library (pip install pulsectl)
"""

from __future__ import annotations

from typing import Optional, Callable
from abc import ABC, abstractmethod
import logging
import queue
import threading

from .base import AudioBackend

logger = logging.getLogger(__name__)

# Type alias for audio callback
AudioCallback = Callable[[bytes, int], None]


class LinuxAudioStrategy(ABC):
    """
    Abstract base class for Linux audio capture strategies.

    Allows switching between PulseAudio and PipeWire implementations.
    """

    @abstractmethod
    def connect(self) -> None:
        """Connect to the audio server."""
        pass

    @abstractmethod
    def find_process_stream(self, pid: int) -> bool:
        """
        Find audio stream for the target process.

        Args:
            pid: Process ID to find

        Returns:
            True if stream found, False otherwise
        """
        pass

    @abstractmethod
    def start_capture(self) -> None:
        """Start capturing audio from the target stream."""
        pass

    @abstractmethod
    def stop_capture(self) -> None:
        """Stop capturing audio."""
        pass

    @abstractmethod
    def read_audio(self, timeout: float = 0.1) -> Optional[bytes]:
        """
        Read audio data from capture buffer.

        Args:
            timeout: Maximum time to wait for data

        Returns:
            PCM audio data as bytes, or None if no data available
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    def get_format(self) -> dict[str, int | object]:
        """
        Get audio format information.

        Returns:
            Dictionary with 'sample_rate', 'channels', 'bits_per_sample'
        """
        pass


class PulseAudioStrategy(LinuxAudioStrategy):
    """
    PulseAudio-based audio capture strategy.

    Uses pulsectl library to interact with PulseAudio server.
    Works on systems with PulseAudio or PipeWire (via pulseaudio-compat layer).
    """

    def __init__(
        self,
        pid: int,
        sample_rate: int = 44100,
        channels: int = 2,
        sample_width: int = 2,
    ) -> None:
        """
        Initialize PulseAudio strategy.

        Args:
            pid: Target process ID
            sample_rate: Sample rate in Hz (default: 44100)
            channels: Number of channels (default: 2 for stereo)
            sample_width: Bytes per sample (default: 2 for 16-bit)
        """
        self._pid = pid
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width
        self._bits_per_sample = sample_width * 8

        self._pulse = None
        self._sink_input_index = None
        self._loopback_module_index = None
        self._capture_stream = None
        self._audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=100)
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Try to import pulsectl
        try:
            import pulsectl
            self._pulsectl = pulsectl
        except ImportError as e:
            raise RuntimeError(
                "pulsectl library is required for Linux audio capture. "
                "Install it with: pip install pulsectl"
            ) from e

    def connect(self) -> None:
        """Connect to PulseAudio server."""
        try:
            self._pulse = self._pulsectl.Pulse('proctap')
            logger.info("Connected to PulseAudio server")
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to PulseAudio server: {e}. "
                "Make sure PulseAudio or PipeWire (with pulseaudio-compat) is running."
            ) from e

    def find_process_stream(self, pid: int) -> bool:
        """
        Find sink-input for the target process.

        Args:
            pid: Process ID to find

        Returns:
            True if stream found, False otherwise

        Raises:
            RuntimeError: If not connected to PulseAudio
        """
        if self._pulse is None:
            raise RuntimeError("Not connected to PulseAudio. Call connect() first.")

        try:
            sink_inputs = self._pulse.sink_input_list()
            logger.debug(f"Found {len(sink_inputs)} sink inputs")

            for sink_input in sink_inputs:
                # Check application.process.id property
                process_id_str = sink_input.proplist.get('application.process.id')
                if process_id_str and process_id_str == str(pid):
                    self._sink_input_index = sink_input.index
                    logger.info(
                        f"Found sink-input #{sink_input.index} for PID {pid}: "
                        f"{sink_input.proplist.get('application.name', 'Unknown')}"
                    )
                    return True

            logger.warning(f"No audio stream found for PID {pid}")
            return False

        except Exception as e:
            logger.error(f"Error finding process stream: {e}")
            return False

    def start_capture(self) -> None:
        """
        Start capturing audio from the target stream.

        Creates a loopback module to capture audio from the sink-input.

        Raises:
            RuntimeError: If sink-input not found or capture fails to start
        """
        if self._sink_input_index is None:
            raise RuntimeError(
                "No sink-input found. Call find_process_stream() first."
            )

        try:
            # Get sink-input details
            sink_input = self._pulse.sink_input_info(self._sink_input_index)
            sink_index = sink_input.sink

            # Create monitor source name
            sink_info = self._pulse.sink_info(sink_index)
            monitor_source = sink_info.monitor_source_name

            # Load module-loopback to capture from this specific sink-input
            # Note: This creates a loopback from the entire sink, not per-app
            # A better approach would use module-remap-source, but that's more complex

            logger.info(f"Creating loopback from sink {sink_index} (monitor: {monitor_source})")

            # For now, we'll use a simpler approach: create a simple recorder
            # that reads from the monitor source and filters by checking timestamps
            # TODO: Implement proper per-sink-input capture using module-remap-source

            # Start capture thread
            self._stop_event.clear()
            self._capture_thread = threading.Thread(
                target=self._capture_worker,
                args=(monitor_source,),
                daemon=True
            )
            self._capture_thread.start()

            logger.info("Audio capture started")

        except Exception as e:
            raise RuntimeError(f"Failed to start audio capture: {e}") from e

    def _capture_worker(self, source_name: str) -> None:
        """
        Worker thread that captures audio from PulseAudio.

        Args:
            source_name: Name of the source to capture from
        """
        try:
            # Create a simple recorder using pulsectl
            # Note: This is a simplified implementation
            # For production, we'd need more sophisticated stream handling

            import subprocess

            # Use parec (PulseAudio recorder) to capture raw PCM
            cmd = [
                'parec',
                '--device', source_name,
                '--rate', str(self._sample_rate),
                '--channels', str(self._channels),
                '--format', 's16le',  # 16-bit signed little-endian
                '--raw'
            ]

            logger.debug(f"Starting parec: {' '.join(cmd)}")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )

            # Read in chunks (10ms of audio)
            chunk_frames = int(self._sample_rate * 0.01)  # 10ms
            chunk_bytes = chunk_frames * self._channels * self._sample_width

            while not self._stop_event.is_set():
                try:
                    if proc.stdout is None:
                        break
                    chunk = proc.stdout.read(chunk_bytes)
                    if not chunk:
                        break

                    if len(chunk) == chunk_bytes:
                        try:
                            self._audio_queue.put_nowait(chunk)
                        except queue.Full:
                            # Drop old frames if queue is full
                            try:
                                self._audio_queue.get_nowait()
                                self._audio_queue.put_nowait(chunk)
                            except:
                                pass

                except Exception as e:
                    logger.error(f"Error reading audio: {e}")
                    break

            # Clean up
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()

            logger.debug("Capture worker stopped")

        except Exception as e:
            logger.error(f"Capture worker error: {e}")

    def stop_capture(self) -> None:
        """Stop capturing audio."""
        self._stop_event.set()

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)

        # Unload loopback module if it exists
        if self._pulse and self._loopback_module_index is not None:
            try:
                self._pulse.module_unload(self._loopback_module_index)
                logger.debug(f"Unloaded loopback module #{self._loopback_module_index}")
            except Exception as e:
                logger.warning(f"Failed to unload loopback module: {e}")
            finally:
                self._loopback_module_index = None

        logger.info("Audio capture stopped")

    def read_audio(self, timeout: float = 0.1) -> Optional[bytes]:
        """
        Read audio data from capture buffer.

        Args:
            timeout: Maximum time to wait for data

        Returns:
            PCM audio data as bytes, or None if no data available
        """
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        """Clean up resources."""
        self.stop_capture()

        if self._pulse:
            self._pulse.close()
            self._pulse = None
            logger.debug("Closed PulseAudio connection")

    def get_format(self) -> dict[str, int | object]:
        """Get audio format information."""
        return {
            'sample_rate': self._sample_rate,
            'channels': self._channels,
            'bits_per_sample': self._bits_per_sample,
        }


class LinuxBackend(AudioBackend):
    """
    Linux implementation for process-specific audio capture.

    ⚠️ EXPERIMENTAL: This backend uses PulseAudio and is in early testing phase.

    Supports:
    - PulseAudio (via pulsectl library)
    - PipeWire (via PulseAudio compatibility layer)

    Requirements:
    - Linux with PulseAudio or PipeWire
    - pulsectl library: pip install pulsectl
    - parec command (usually in pulseaudio-utils package)

    Limitations:
    - Currently captures from the entire sink monitor (not per-application isolation)
    - Requires the target process to be actively playing audio
    - May capture audio from other applications on the same sink

    TODO: Implement proper per-application isolation using module-remap-source
    """

    def __init__(
        self,
        pid: int,
        sample_rate: int = 44100,
        channels: int = 2,
        sample_width: int = 2,
        engine: str = "auto",
    ) -> None:
        """
        Initialize Linux backend.

        Args:
            pid: Process ID to capture audio from
            sample_rate: Sample rate in Hz (default: 44100)
            channels: Number of channels (default: 2 for stereo)
            sample_width: Bytes per sample (default: 2 for 16-bit)
            engine: Audio engine to use: "auto", "pulse", or "pipewire"
                   (default: "auto" - currently uses PulseAudio)
        """
        super().__init__(pid)

        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width
        self._engine = engine
        self._is_running = False

        # Select strategy based on engine parameter
        if engine in ("auto", "pulse"):
            self._strategy: LinuxAudioStrategy = PulseAudioStrategy(
                pid=pid,
                sample_rate=sample_rate,
                channels=channels,
                sample_width=sample_width,
            )
            logger.info(f"Initialized LinuxBackend for PID {pid} (engine: PulseAudio)")
        elif engine == "pipewire":
            # Future: PipeWireStrategy implementation
            raise NotImplementedError(
                "Native PipeWire backend is not yet implemented. "
                "Use engine='auto' or 'pulse' to use PulseAudio compatibility layer."
            )
        else:
            raise ValueError(f"Unknown engine: {engine}. Use 'auto', 'pulse', or 'pipewire'")

    def start(self) -> None:
        """
        Start audio capture from the target process.

        Raises:
            RuntimeError: If capture fails to start
        """
        if self._is_running:
            logger.warning("Audio capture is already running")
            return

        try:
            # Connect to audio server
            self._strategy.connect()

            # Find process stream
            if not self._strategy.find_process_stream(self._pid):
                raise RuntimeError(
                    f"No audio stream found for PID {self._pid}. "
                    "Make sure the process is actively playing audio."
                )

            # Start capture
            self._strategy.start_capture()
            self._is_running = True

            logger.info(f"Started audio capture for PID {self._pid}")

        except Exception as e:
            self._is_running = False
            raise RuntimeError(f"Failed to start audio capture: {e}") from e

    def stop(self) -> None:
        """Stop audio capture."""
        if not self._is_running:
            return

        try:
            self._strategy.stop_capture()
            self._is_running = False
            logger.info("Stopped audio capture")
        except Exception as e:
            logger.error(f"Error stopping capture: {e}")

    def read(self) -> Optional[bytes]:
        """
        Read audio data from the capture buffer.

        Returns:
            PCM audio data as bytes, or None if no data is available
        """
        if not self._is_running:
            return None

        return self._strategy.read_audio(timeout=0.1)

    def get_format(self) -> dict[str, int | object]:
        """
        Get audio format information.

        Returns:
            Dictionary with 'sample_rate', 'channels', 'bits_per_sample'
        """
        return self._strategy.get_format()

    def close(self) -> None:
        """Clean up resources."""
        self.stop()
        if self._strategy:
            self._strategy.close()

    def __del__(self) -> None:
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except:
            pass


# Development notes:
#
# Current implementation limitations:
# - Uses `parec` to capture from monitor source (entire sink, not per-app)
# - This means it may capture audio from other apps using the same sink
# - Proper per-app isolation requires module-remap-source or similar
#
# Future improvements:
# 1. Implement proper per-sink-input capture using module-remap-source
# 2. Add native PipeWire support (PipeWireStrategy class)
# 3. Improve error handling for edge cases
# 4. Add support for dynamic format negotiation
# 5. Optimize buffer management for lower latency
#
# References:
# - PulseAudio module-remap-source: https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/Modules/#module-remap-source
# - pulsectl documentation: https://github.com/mk-fg/python-pulse-control
# - PipeWire PulseAudio compatibility: https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/Config-PulseAudio
