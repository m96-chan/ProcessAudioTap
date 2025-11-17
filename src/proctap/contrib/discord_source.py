"""
Discord AudioSource implementation for proctap.

Streams process audio to Discord voice channels with automatic format conversion
and resampling to Discord's required format (48kHz, 16-bit PCM, stereo).
"""

from __future__ import annotations

import logging
import struct
import threading
import time
from collections import deque
from typing import Optional

import numpy as np

try:
    import discord
except ImportError as e:
    raise ImportError(
        "discord.py is required for ProcessAudioSource. "
        "Install with: pip install discord.py"
    ) from e

from ..core import ProcessAudioCapture

logger = logging.getLogger(__name__)

# Discord audio constants
DISCORD_SAMPLE_RATE = 48000  # Hz
DISCORD_CHANNELS = 2  # Stereo
DISCORD_SAMPLE_SIZE = 2  # 16-bit = 2 bytes
DISCORD_FRAME_DURATION_MS = 20  # ms
DISCORD_SAMPLES_PER_FRAME = int(DISCORD_SAMPLE_RATE * DISCORD_FRAME_DURATION_MS / 1000)
DISCORD_FRAME_SIZE = DISCORD_SAMPLES_PER_FRAME * DISCORD_CHANNELS * DISCORD_SAMPLE_SIZE  # 3840 bytes


class ProcessAudioSource(discord.AudioSource):
    """
    Discord AudioSource that captures audio from a specific process.

    This class streams audio from a target process to Discord voice channels,
    automatically handling format detection, conversion, and resampling.

    Args:
        pid: Process ID to capture audio from
        gain: Audio gain multiplier (default: 1.0)
        max_queue_frames: Maximum frames to buffer (default: 50)

    Example:
        ```python
        import discord
        from processaudiotap.contrib import ProcessAudioSource

        # In your Discord bot
        voice_client = await channel.connect()
        source = ProcessAudioSource(pid=12345, gain=1.2)
        voice_client.play(source)
        ```

    Note:
        - Automatically resamples from native 44.1kHz to Discord's 48kHz
        - Handles both 32-bit float and 16-bit PCM input formats
        - Runs capture in a separate thread for minimal latency
    """

    def __init__(
        self,
        pid: int,
        gain: float = 1.0,
        max_queue_frames: int = 50,
    ) -> None:
        self.pid = pid
        self.gain = gain
        self.max_queue_frames = max_queue_frames

        self._tap: Optional[ProcessAudioCapture] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Audio queue and buffer
        self._audio_queue: deque[bytes] = deque(maxlen=max_queue_frames)
        self._queue_lock = threading.Lock()
        self._buffer = bytearray()

        # Format detection
        self._source_format: Optional[dict[str, int]] = None
        self._is_float32 = False
        self._format_detected = False

        # Statistics
        self._frames_dropped = 0
        self._frames_served = 0

        logger.info(f"ProcessAudioSource created for PID {pid} (gain={gain})")

    def start(self) -> None:
        """Start audio capture from the target process."""
        if self._capture_thread is not None:
            logger.warning("Audio capture already started")
            return

        logger.info(f"Starting audio capture for PID {self.pid}")

        # Create ProcessAudioCapture
        self._tap = ProcessAudioCapture(pid=self.pid)
        self._tap.start()

        # Get source format
        self._source_format = self._tap.get_format()
        logger.info(f"Source format: {self._source_format}")

        # Start capture thread
        self._stop_event.clear()
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name=f"ProcessAudioSource-{self.pid}"
        )
        self._capture_thread.start()

        logger.info("Audio capture started")

    def stop(self) -> None:
        """Stop audio capture and release resources."""
        if self._capture_thread is None:
            return

        logger.info("Stopping audio capture...")
        self._stop_event.set()

        if self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None

        if self._tap is not None:
            try:
                self._tap.close()
            except Exception:
                logger.exception("Error closing ProcessAudioCapture")
            finally:
                self._tap = None

        logger.info(
            f"Audio capture stopped. Stats: served={self._frames_served}, dropped={self._frames_dropped}"
        )

    def _capture_loop(self) -> None:
        """
        Capture loop running in separate thread.
        Continuously reads audio from ProcessAudioCapture and queues converted frames.
        """
        logger.debug("Capture loop started")

        while not self._stop_event.is_set():
            try:
                # Read audio with timeout
                if self._tap is None:
                    break
                chunk = self._tap.read(timeout=0.5)

                if chunk is None or len(chunk) == 0:
                    continue

                # Detect format on first chunk
                if not self._format_detected:
                    self._detect_format(chunk)

                # Convert and resample audio
                converted = self._convert_audio(chunk)

                if converted:
                    with self._queue_lock:
                        try:
                            self._audio_queue.append(converted)
                        except IndexError:
                            # Queue full, frame dropped
                            self._frames_dropped += 1

            except Exception:
                logger.exception("Error in capture loop")
                time.sleep(0.1)  # Prevent busy loop on error

        logger.debug("Capture loop ended")

    def _detect_format(self, chunk: bytes) -> None:
        """
        Detect if audio data is 32-bit float or 16-bit PCM.

        WASAPI may return 32-bit float despite requesting 16-bit PCM.
        """
        if self._format_detected:
            return

        if len(chunk) < 8:
            return  # Not enough data to detect

        # Try to interpret as 32-bit float
        try:
            sample_count = len(chunk) // 4
            floats = struct.unpack(f"{sample_count}f", chunk[:sample_count * 4])

            # Check if values are in typical float range [-1.0, 1.0]
            max_abs = max(abs(f) for f in floats[:min(100, len(floats))])

            if 0.0 < max_abs <= 2.0:  # Likely float32
                self._is_float32 = True
                logger.info("Detected 32-bit float PCM format")
            else:
                self._is_float32 = False
                logger.info("Detected 16-bit PCM format")

        except struct.error:
            self._is_float32 = False
            logger.info("Defaulting to 16-bit PCM format")

        self._format_detected = True

    def _convert_audio(self, chunk: bytes) -> Optional[bytes]:
        """
        Convert audio to Discord format (48kHz, 16-bit PCM, stereo).

        Args:
            chunk: Raw audio data from ProcessAudioCapture

        Returns:
            Converted audio data, or None if conversion failed
        """
        if not self._source_format:
            return None

        try:
            # Parse audio data
            if self._is_float32:
                # 32-bit float PCM
                sample_count = len(chunk) // 4
                audio_data = np.frombuffer(chunk, dtype=np.float32, count=sample_count)

                # Check for NaN/Inf
                if np.any(~np.isfinite(audio_data)):
                    logger.warning("NaN/Inf detected in audio data, skipping frame")
                    return None

                # Convert float32 [-1.0, 1.0] to int16
                audio_data = np.clip(audio_data * 32767.0 * self.gain, -32768, 32767)
                audio_data = audio_data.astype(np.int16)
            else:
                # 16-bit PCM
                sample_count = len(chunk) // 2
                audio_data = np.frombuffer(chunk, dtype=np.int16, count=sample_count)

                # Apply gain
                if self.gain != 1.0:
                    audio_data = audio_data.astype(np.float32)
                    audio_data = np.clip(audio_data * self.gain, -32768, 32767)
                    audio_data = audio_data.astype(np.int16)

            # Reshape to (frames, channels)
            channels = self._source_format["channels"]
            frames = len(audio_data) // channels

            if frames == 0:
                return None

            audio_data = audio_data[:frames * channels].reshape(frames, channels)

            # Handle mono to stereo conversion
            if channels == 1:
                audio_data = np.repeat(audio_data, 2, axis=1)

            # Resample if necessary
            source_rate = self._source_format["sample_rate"]
            if source_rate != DISCORD_SAMPLE_RATE:
                audio_data = self._resample(audio_data, source_rate, DISCORD_SAMPLE_RATE)

            # Convert to bytes
            return audio_data.tobytes()

        except Exception:
            logger.exception("Error converting audio")
            return None

    def _resample(
        self,
        audio: np.ndarray,
        source_rate: int,
        target_rate: int
    ) -> np.ndarray:
        """
        Resample audio using linear interpolation.

        Args:
            audio: Audio data shaped (frames, channels)
            source_rate: Source sample rate
            target_rate: Target sample rate

        Returns:
            Resampled audio data
        """
        if source_rate == target_rate:
            return audio

        # Calculate resampling ratio
        ratio = target_rate / source_rate
        source_frames = len(audio)
        target_frames = int(source_frames * ratio)

        # Linear interpolation for each channel
        source_indices = np.arange(source_frames)
        target_indices = np.linspace(0, source_frames - 1, target_frames)

        resampled = np.empty((target_frames, audio.shape[1]), dtype=audio.dtype)

        for ch in range(audio.shape[1]):
            resampled[:, ch] = np.interp(target_indices, source_indices, audio[:, ch])

        return resampled

    def read(self) -> bytes:
        """
        Read one Discord audio frame (20ms @ 48kHz = 3840 bytes).

        This method is called by discord.py's voice client.

        Returns:
            3840 bytes of 16-bit PCM stereo audio, or silence if no data available
        """
        # Accumulate data until we have a full Discord frame
        while len(self._buffer) < DISCORD_FRAME_SIZE:
            with self._queue_lock:
                if not self._audio_queue:
                    # No data available, return silence
                    silence = b"\x00" * DISCORD_FRAME_SIZE
                    return silence

                chunk = self._audio_queue.popleft()
                self._buffer.extend(chunk)

        # Extract one Discord frame
        frame = bytes(self._buffer[:DISCORD_FRAME_SIZE])
        del self._buffer[:DISCORD_FRAME_SIZE]

        self._frames_served += 1
        return frame

    def is_opus(self) -> bool:
        """
        Indicate whether this source provides Opus-encoded audio.

        Returns:
            False (this source provides raw PCM)
        """
        return False

    def cleanup(self) -> None:
        """
        Cleanup resources when discord.py is done with this source.

        This is called automatically by discord.py.
        """
        self.stop()

    @property
    def stats(self) -> dict[str, int]:
        """
        Get capture statistics.

        Returns:
            Dictionary with keys:
            - 'frames_served': Number of frames successfully served
            - 'frames_dropped': Number of frames dropped due to queue overflow
            - 'queue_size': Current number of frames in queue
        """
        with self._queue_lock:
            queue_size = len(self._audio_queue)

        return {
            "frames_served": self._frames_served,
            "frames_dropped": self._frames_dropped,
            "queue_size": queue_size,
        }
