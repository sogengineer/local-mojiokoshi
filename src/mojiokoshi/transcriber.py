"""Whisper transcription engine using mlx-whisper."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import mlx_whisper


@dataclass
class TranscriptionResult:
    """Result of transcription."""
    text: str
    segments: list
    language: str


ModelSize = Literal["tiny", "base", "small", "medium", "large-v3"]


class WhisperTranscriber:
    """Transcriber using mlx-whisper for Apple Silicon."""

    MODELS = {
        "tiny": "mlx-community/whisper-tiny-mlx",
        "base": "mlx-community/whisper-base-mlx",
        "small": "mlx-community/whisper-small-mlx",
        "medium": "mlx-community/whisper-medium-mlx",
        "large-v3": "mlx-community/whisper-large-v3-mlx",
    }

    def __init__(
        self,
        model_name: ModelSize = "large-v3",
        language: str = "ja",
    ):
        self.model_path = self.MODELS[model_name]
        self.language = language
        self.model_name = model_name

    def transcribe(self, audio_path: Path | str) -> TranscriptionResult:
        """Transcribe audio file to text."""
        audio_path = str(audio_path)

        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo=self.model_path,
            language=self.language,
            word_timestamps=False,
        )

        return TranscriptionResult(
            text=result["text"].strip(),
            segments=result.get("segments", []),
            language=result.get("language", self.language),
        )
