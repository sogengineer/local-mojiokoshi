"""Tests for realtime transcription module."""

import threading

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from mojiokoshi.realtime import RealtimeTranscriber


class TestRealtimeTranscriber:
    """Tests for RealtimeTranscriber class."""

    @patch("mojiokoshi.realtime.WhisperTranscriber")
    @patch("mojiokoshi.realtime.MicrophoneRecorder")
    def test_init_defaults(self, mock_recorder_cls, mock_transcriber_cls):
        """Test default initialization."""
        rt = RealtimeTranscriber()
        assert rt.silence_threshold == 0.01
        assert rt.silence_duration == 1.5
        assert rt.min_audio_length == 1.0
        mock_recorder_cls.assert_called_once_with(device=None)
        mock_transcriber_cls.assert_called_once_with(model_name="large-v3", language="ja")

    @patch("mojiokoshi.realtime.WhisperTranscriber")
    @patch("mojiokoshi.realtime.MicrophoneRecorder")
    def test_get_all_text_empty(self, mock_recorder_cls, mock_transcriber_cls):
        """Test get_all_text returns empty string initially."""
        rt = RealtimeTranscriber()
        assert rt.get_all_text() == ""

    @patch("mojiokoshi.realtime.WhisperTranscriber")
    @patch("mojiokoshi.realtime.MicrophoneRecorder")
    def test_get_all_text_with_data(self, mock_recorder_cls, mock_transcriber_cls):
        """Test get_all_text returns accumulated text."""
        rt = RealtimeTranscriber()
        rt._all_text = ["Hello", "World"]
        assert rt.get_all_text() == "Hello\nWorld"

    @patch("mojiokoshi.realtime.WhisperTranscriber")
    @patch("mojiokoshi.realtime.MicrophoneRecorder")
    def test_process_chunk_silence_ignored(self, mock_recorder_cls, mock_transcriber_cls):
        """Test that silent chunks are ignored when not speaking."""
        rt = RealtimeTranscriber(silence_threshold=0.5)
        silent_chunk = np.zeros(100, dtype=np.float32)
        rt._process_chunk(silent_chunk)
        assert len(rt._buffer) == 0

    @patch("mojiokoshi.realtime.WhisperTranscriber")
    @patch("mojiokoshi.realtime.MicrophoneRecorder")
    def test_process_chunk_speech_buffered(self, mock_recorder_cls, mock_transcriber_cls):
        """Test that speech chunks are added to buffer."""
        rt = RealtimeTranscriber(silence_threshold=0.01)
        speech_chunk = np.ones(100, dtype=np.float32)
        rt._process_chunk(speech_chunk)
        assert len(rt._buffer) == 1
        assert rt._is_speaking is True

    @patch("mojiokoshi.realtime.WhisperTranscriber")
    @patch("mojiokoshi.realtime.MicrophoneRecorder")
    def test_stop_event_used(self, mock_recorder_cls, mock_transcriber_cls):
        """Test that _stop_event is a threading.Event."""
        rt = RealtimeTranscriber()
        assert isinstance(rt._stop_event, threading.Event)
        assert not rt._stop_event.is_set()
