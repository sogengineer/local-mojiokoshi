"""Tests for transcriber module."""

import pytest
from mojiokoshi.transcriber import WhisperTranscriber, TranscriptionResult


class TestWhisperTranscriber:
    """Tests for WhisperTranscriber class."""

    def test_init_default_model(self):
        """Test default model initialization."""
        transcriber = WhisperTranscriber()
        assert transcriber.model_name == "large-v3"
        assert transcriber.language == "ja"
        assert transcriber.model_path == "mlx-community/whisper-large-v3-mlx"

    def test_init_custom_model(self):
        """Test custom model initialization."""
        transcriber = WhisperTranscriber(model_name="base", language="en")
        assert transcriber.model_name == "base"
        assert transcriber.language == "en"
        assert transcriber.model_path == "mlx-community/whisper-base-mlx"

    def test_models_dict(self):
        """Test all models are correctly mapped."""
        expected_models = {
            "tiny": "mlx-community/whisper-tiny-mlx",
            "base": "mlx-community/whisper-base-mlx",
            "small": "mlx-community/whisper-small-mlx",
            "medium": "mlx-community/whisper-medium-mlx",
            "large-v3": "mlx-community/whisper-large-v3-mlx",
        }
        assert WhisperTranscriber.MODELS == expected_models

    def test_invalid_model_raises_error(self):
        """Test that invalid model name raises KeyError."""
        with pytest.raises(KeyError):
            WhisperTranscriber(model_name="invalid")


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_creation(self):
        """Test TranscriptionResult creation."""
        result = TranscriptionResult(
            text="Hello world",
            segments=[{"start": 0, "end": 1, "text": "Hello world"}],
            language="en",
        )
        assert result.text == "Hello world"
        assert len(result.segments) == 1
        assert result.language == "en"
