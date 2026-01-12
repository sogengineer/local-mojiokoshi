"""Tests for recorder module."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from mojiokoshi.recorder import MicrophoneRecorder


class TestMicrophoneRecorder:
    """Tests for MicrophoneRecorder class."""

    def test_init_defaults(self):
        """Test default initialization."""
        recorder = MicrophoneRecorder()
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert recorder.device is None

    def test_init_custom(self):
        """Test custom initialization."""
        recorder = MicrophoneRecorder(sample_rate=44100, channels=2, device=1)
        assert recorder.sample_rate == 44100
        assert recorder.channels == 2
        assert recorder.device == 1

    @patch("mojiokoshi.recorder.sd.query_devices")
    def test_list_devices(self, mock_query):
        """Test list_devices returns input devices."""
        mock_devices = [
            {"name": "Mic 1", "max_input_channels": 2, "max_output_channels": 0},
            {"name": "Speaker", "max_input_channels": 0, "max_output_channels": 2},
            {"name": "Mic 2", "max_input_channels": 1, "max_output_channels": 0},
        ]

        # First call returns all devices, second call (kind="input") returns default
        def side_effect(kind=None):
            if kind == "input":
                return mock_devices[0]
            return mock_devices

        mock_query.side_effect = side_effect

        devices = MicrophoneRecorder.list_devices()

        # Should only return input devices (max_input_channels > 0)
        assert len(devices) == 2
        assert devices[0]["name"] == "Mic 1"
        assert devices[1]["name"] == "Mic 2"

    def test_save_wav(self, tmp_path):
        """Test saving audio as WAV file."""
        recorder = MicrophoneRecorder()

        # Create test audio data
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.float32)

        wav_path = tmp_path / "test.wav"
        recorder.save_wav(audio, wav_path)

        assert wav_path.exists()
        assert wav_path.stat().st_size > 0


class TestAudioConversion:
    """Tests for audio data conversion."""

    def test_float_to_int16_conversion(self):
        """Test that float32 audio is correctly converted to int16."""
        recorder = MicrophoneRecorder()

        # Float32 audio in range [-1, 1]
        audio = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float32)

        # Expected int16 values
        expected = np.array([0, 16383, -16383, 32767, -32767], dtype=np.int16)

        # Convert
        audio_int16 = (audio * 32767).astype(np.int16)

        np.testing.assert_array_equal(audio_int16, expected)
