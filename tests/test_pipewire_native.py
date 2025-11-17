"""
Tests for PipeWire native API bindings.

These tests verify the ctypes bindings and API wrapper functionality.
Note: Some tests require a running PipeWire daemon.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# Import the module
try:
    from proctap.backends import pipewire_native
except ImportError:
    pytest.skip("PipeWire native bindings not available", allow_module_level=True)


class TestPipeWireAvailability:
    """Test PipeWire library availability checks."""

    def test_is_available(self):
        """Test is_available() function."""
        # Should return a boolean
        result = pipewire_native.is_available()
        assert isinstance(result, bool)

    def test_library_loading(self):
        """Test library loading succeeds or fails gracefully."""
        if pipewire_native.is_available():
            # If available, _pw_lib should be set
            assert pipewire_native._pw_lib is not None
        else:
            # If not available, _pw_lib should be None
            assert pipewire_native._pw_lib is None


class TestErrorHandling:
    """Test error handling utilities."""

    def test_get_error_string_success(self):
        """Test error string for success (0)."""
        if not pipewire_native.is_available():
            pytest.skip("PipeWire not available")

        msg = pipewire_native._get_error_string(0)
        assert msg == "Success"

    def test_get_error_string_errno(self):
        """Test error string for common errno values."""
        if not pipewire_native.is_available():
            pytest.skip("PipeWire not available")

        # Test EINVAL (22)
        msg = pipewire_native._get_error_string(-22)
        assert "errno 22" in msg
        assert "Invalid argument" in msg

    def test_get_error_string_unknown(self):
        """Test error string for unknown error code."""
        if not pipewire_native.is_available():
            pytest.skip("PipeWire not available")

        msg = pipewire_native._get_error_string(-99999)
        assert "errno 99999" in msg
        assert "Unknown error" in msg


class TestExceptionTypes:
    """Test custom exception types."""

    def test_pipewire_error_hierarchy(self):
        """Test exception inheritance hierarchy."""
        assert issubclass(pipewire_native.PipeWireError, Exception)
        assert issubclass(pipewire_native.PipeWireInitError, pipewire_native.PipeWireError)
        assert issubclass(pipewire_native.PipeWireStreamError, pipewire_native.PipeWireError)
        assert issubclass(pipewire_native.PipeWireRegistryError, pipewire_native.PipeWireError)

    def test_exception_messages(self):
        """Test exception message passing."""
        msg = "Test error message"
        exc = pipewire_native.PipeWireError(msg)
        assert str(exc) == msg


class TestEnumDefinitions:
    """Test enum definitions."""

    def test_pw_direction_enum(self):
        """Test PWDirection enum values."""
        assert pipewire_native.PWDirection.INPUT == 1
        assert pipewire_native.PWDirection.OUTPUT == 2

    def test_pw_stream_state_enum(self):
        """Test PWStreamState enum values."""
        assert pipewire_native.PWStreamState.ERROR == -1
        assert pipewire_native.PWStreamState.UNCONNECTED == 0
        assert pipewire_native.PWStreamState.CONNECTING == 1
        assert pipewire_native.PWStreamState.PAUSED == 2
        assert pipewire_native.PWStreamState.STREAMING == 3

    def test_spa_type_enum(self):
        """Test SPAType enum values."""
        assert pipewire_native.SPAType.NONE == 0
        assert pipewire_native.SPAType.INT == 3
        assert pipewire_native.SPAType.ID == 2
        assert pipewire_native.SPAType.OBJECT == 14

    def test_spa_audio_format_enum(self):
        """Test SPAAudioFormat enum values."""
        assert pipewire_native.SPAAudioFormat.UNKNOWN == 0
        assert pipewire_native.SPAAudioFormat.S16_LE == 4
        assert pipewire_native.SPAAudioFormat.F32_LE == 20


class TestSPAConstants:
    """Test SPA format constants."""

    def test_spa_format_constants(self):
        """Test SPA format property IDs."""
        assert pipewire_native.SPA_FORMAT_mediaType == 0x00001
        assert pipewire_native.SPA_FORMAT_mediaSubtype == 0x00002
        assert pipewire_native.SPA_FORMAT_AUDIO_format == 0x10001
        assert pipewire_native.SPA_FORMAT_AUDIO_rate == 0x10003
        assert pipewire_native.SPA_FORMAT_AUDIO_channels == 0x10004

    def test_spa_media_type_constants(self):
        """Test SPA media type constants."""
        assert pipewire_native.SPA_MEDIA_TYPE_audio == 1
        assert pipewire_native.SPA_MEDIA_SUBTYPE_raw == 1


@pytest.mark.skipif(not pipewire_native.is_available(), reason="PipeWire not available")
class TestPipeWireNativeClass:
    """Test PipeWireNative wrapper class."""

    def test_initialization(self):
        """Test PipeWireNative initialization."""
        pw = pipewire_native.PipeWireNative()
        assert pw is not None
        assert not pw._initialized

    def test_singleton_pattern(self):
        """Test get_pipewire_native() singleton."""
        pw1 = pipewire_native.get_pipewire_native()
        pw2 = pipewire_native.get_pipewire_native()
        assert pw1 is pw2


@pytest.mark.skipif(not pipewire_native.is_available(), reason="PipeWire not available")
class TestPipeWireStreamCapture:
    """Test PipeWireStreamCapture class."""

    def test_initialization(self):
        """Test stream capture initialization."""
        capture = pipewire_native.PipeWireStreamCapture(
            sample_rate=48000,
            channels=2,
            on_data=lambda data, frames: None
        )
        assert capture is not None
        assert capture._sample_rate == 48000
        assert capture._channels == 2
        assert not capture._running

    def test_initialization_custom_params(self):
        """Test stream capture with custom parameters."""
        capture = pipewire_native.PipeWireStreamCapture(
            sample_rate=44100,
            channels=1,
            on_data=None
        )
        assert capture._sample_rate == 44100
        assert capture._channels == 1


@pytest.mark.skipif(not pipewire_native.is_available(), reason="PipeWire not available")
class TestPipeWireNodeDiscovery:
    """Test PipeWireNodeDiscovery class."""

    def test_initialization(self):
        """Test node discovery initialization."""
        discovery = pipewire_native.PipeWireNodeDiscovery()
        assert discovery is not None
        assert discovery._target_pid is None
        assert len(discovery._found_nodes) == 0


class TestBuildAudioFormatParams:
    """Test build_audio_format_params function."""

    @pytest.mark.skipif(not pipewire_native.is_available(), reason="PipeWire not available")
    def test_build_format_params_basic(self):
        """Test building basic audio format parameters."""
        params_ptr, buffer_size = pipewire_native.build_audio_format_params(
            sample_rate=48000,
            channels=2,
            audio_format=pipewire_native.SPAAudioFormat.S16_LE
        )

        # Should return non-null pointer and reasonable buffer size
        assert params_ptr is not None
        assert buffer_size > 0
        assert buffer_size <= 1024  # Should fit in allocated buffer

    @pytest.mark.skipif(not pipewire_native.is_available(), reason="PipeWire not available")
    def test_build_format_params_mono(self):
        """Test building mono format parameters."""
        params_ptr, buffer_size = pipewire_native.build_audio_format_params(
            sample_rate=44100,
            channels=1
        )
        assert params_ptr is not None

    @pytest.mark.skipif(not pipewire_native.is_available(), reason="PipeWire not available")
    def test_build_format_params_different_rates(self):
        """Test building parameters with different sample rates."""
        for rate in [44100, 48000, 96000]:
            params_ptr, _ = pipewire_native.build_audio_format_params(
                sample_rate=rate,
                channels=2
            )
            assert params_ptr is not None


# Integration tests (require running PipeWire daemon)
@pytest.mark.integration
@pytest.mark.skipif(not pipewire_native.is_available(), reason="PipeWire not available")
class TestPipeWireIntegration:
    """Integration tests requiring running PipeWire daemon."""

    def test_init_and_deinit(self):
        """Test PipeWire initialization and deinitialization."""
        pw = pipewire_native.PipeWireNative()

        try:
            pw.init()
            assert pw._initialized
        finally:
            pw.deinit()
            assert not pw._initialized

    def test_create_main_loop(self):
        """Test main loop creation."""
        pw = pipewire_native.PipeWireNative()

        try:
            pw.init()
            pw.create_main_loop()
            assert pw._main_loop is not None
        finally:
            pw.destroy_main_loop()
            pw.deinit()

    def test_full_initialization_sequence(self):
        """Test full initialization sequence."""
        pw = pipewire_native.PipeWireNative()

        try:
            pw.init()
            pw.create_main_loop()
            pw.create_context()
            pw.connect_core()

            assert pw._initialized
            assert pw._main_loop is not None
            assert pw._context is not None
            assert pw._core is not None
        finally:
            pw.cleanup()


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
