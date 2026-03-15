# パッケージの公開APIを定義する
from .cli import main
from .realtime import RealtimeTranscriber
from .recorder import MicrophoneRecorder
from .transcriber import TranscriptionResult, WhisperTranscriber

__all__ = [
    "main",
    "MicrophoneRecorder",
    "RealtimeTranscriber",
    "TranscriptionResult",
    "WhisperTranscriber",
]
