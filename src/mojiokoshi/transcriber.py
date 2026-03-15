"""Whisper transcription engine using mlx-whisper."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import mlx_whisper

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """文字起こし結果を保持するデータクラス"""
    text: str
    segments: list[dict[str, Any]]
    language: str


# 利用可能なWhisperモデルサイズの型定義
ModelSize = Literal["tiny", "base", "small", "medium", "large-v3"]


class WhisperTranscriber:
    """Apple Silicon向けmlx-whisperを用いた文字起こしエンジン"""

    # モデルサイズ名からHugging Faceリポジトリへのマッピング
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
        """音声ファイルをテキストに変換する"""
        audio_path_str = str(audio_path)

        if not Path(audio_path_str).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path_str}")

        try:
            result = mlx_whisper.transcribe(
                audio_path_str,
                path_or_hf_repo=self.model_path,
                language=self.language,
                word_timestamps=False,
            )
        except Exception as e:
            logger.error("Failed to transcribe %s: %s", audio_path_str, e)
            raise RuntimeError(f"Transcription failed for {audio_path_str}") from e

        return TranscriptionResult(
            text=result["text"].strip(),
            segments=result.get("segments", []),
            language=result.get("language", self.language),
        )
