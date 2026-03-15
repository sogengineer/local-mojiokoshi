"""Realtime transcription with VAD (Voice Activity Detection)."""

import logging
import tempfile
import threading
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.io import wavfile

from .recorder import INT16_MAX, MicrophoneRecorder
from .transcriber import WhisperTranscriber

logger = logging.getLogger(__name__)


class RealtimeTranscriber:
    """音声活動検出(VAD)に基づくリアルタイム文字起こしクラス。
    無音区間を検出して発話単位でWhisperに送る。"""

    def __init__(
        self,
        model_name: str = "large-v3",
        language: str = "ja",
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        min_audio_length: float = 1.0,
        on_transcription: Callable[[str], None] | None = None,
        device: int | None = None,
    ):
        self.recorder = MicrophoneRecorder(device=device)
        self.transcriber = WhisperTranscriber(model_name=model_name, language=language)
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.min_audio_length = min_audio_length
        self.on_transcription = on_transcription or print

        self._buffer: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._silence_samples = 0
        self._is_speaking = False
        self._stop_event = threading.Event()
        self._transcription_thread: threading.Thread | None = None
        self._all_text: list[str] = []

    def _process_chunk(self, chunk: np.ndarray) -> None:
        """音声チャンクのVAD判定を行い、無音が続いたら文字起こしをトリガーする"""
        amplitude = np.abs(chunk).mean()
        is_speech = amplitude > self.silence_threshold

        should_transcribe = False
        with self._lock:
            if is_speech:
                self._buffer.append(chunk)
                self._silence_samples = 0
                self._is_speaking = True
            else:
                if self._is_speaking:
                    self._buffer.append(chunk)
                    self._silence_samples += len(chunk)

                    # 無音が閾値を超えたら発話終了とみなす
                    samples_threshold = int(self.silence_duration * self.recorder.sample_rate)
                    if self._silence_samples >= samples_threshold:
                        should_transcribe = True

        if should_transcribe:
            self._transcribe_buffer()

    def _transcribe_buffer(self) -> None:
        """バッファに蓄積した音声を別スレッドで文字起こしする"""
        with self._lock:
            if not self._buffer:
                return

            audio = np.concatenate(self._buffer).flatten()
            self._buffer = []
            self._is_speaking = False
            self._silence_samples = 0

        # 短すぎる音声は無視する
        min_samples = int(self.min_audio_length * self.recorder.sample_rate)
        if len(audio) < min_samples:
            return

        # 前の文字起こしスレッドの完了を待つ（デッドロック防止のためロック外で実行）
        if self._transcription_thread is not None and self._transcription_thread.is_alive():
            self._transcription_thread.join(timeout=30)

        # 録音コールバックをブロックしないよう別スレッドで文字起こし
        def transcribe() -> None:
            temp_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = Path(f.name)
                    audio_int16 = (audio * INT16_MAX).astype(np.int16)
                    wavfile.write(temp_path, self.recorder.sample_rate, audio_int16)

                result = self.transcriber.transcribe(temp_path)

                if result.text.strip():
                    with self._lock:
                        self._all_text.append(result.text.strip())
                    self.on_transcription(result.text.strip())
            except Exception:
                logger.exception("Transcription error")
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)

        self._transcription_thread = threading.Thread(target=transcribe)
        self._transcription_thread.start()

    def start(self) -> None:
        """リアルタイム文字起こしを開始する（Ctrl+Cで停止）"""
        logger.info("Loading model: %s...", self.transcriber.model_name)
        # モデルの初回ロードを事前に行い、最初の文字起こしの遅延を軽減する
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = Path(f.name)
            silence = np.zeros(self.recorder.sample_rate, dtype=np.int16)
            wavfile.write(temp_path, self.recorder.sample_rate, silence)
        try:
            self.transcriber.transcribe(temp_path)
        except Exception:
            logger.warning("Model warmup failed", exc_info=True)
        finally:
            temp_path.unlink(missing_ok=True)

        logger.info("Realtime transcription started. Press Ctrl+C to stop.")

        self._stop_event.clear()
        self._all_text = []
        self.recorder.start_recording(on_chunk=self._process_chunk)

        # Ctrl+Cまたはstop_eventが発火するまで待機する
        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(0.1)
        except KeyboardInterrupt:
            pass

        self.stop()

    def stop(self) -> str:
        """文字起こしを停止し、残りのバッファを処理してから全テキストを返す"""
        self._stop_event.set()
        self.recorder.stop_recording()

        # 残りのバッファを文字起こし（デッドロック防止のためロック外で実行）
        self._transcribe_buffer()

        # 最後の文字起こしスレッドの完了を待つ
        if self._transcription_thread:
            self._transcription_thread.join(timeout=30)
            if self._transcription_thread.is_alive():
                logger.warning("Transcription thread did not finish in time")

        logger.info("Realtime transcription stopped.")
        with self._lock:
            return "\n".join(self._all_text)

    def get_all_text(self) -> str:
        """これまでに文字起こしした全テキストを取得する"""
        with self._lock:
            return "\n".join(self._all_text)
