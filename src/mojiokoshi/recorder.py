"""Microphone recording module using sounddevice."""

import logging
from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

logger = logging.getLogger(__name__)

# 音声フォーマット定数
INT16_MAX = 32767
CHUNK_DURATION_SEC = 0.5


class MicrophoneRecorder:
    """マイクからの音声録音を管理するクラス。
    ブロッキング録音とストリーミング録音の両方に対応する。"""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device: int | None = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None

    @staticmethod
    def list_devices() -> list[dict]:
        """利用可能な入力デバイスの一覧を取得する"""
        devices = sd.query_devices()
        result = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                result.append({
                    "id": i,
                    "name": d["name"],
                    "channels": d["max_input_channels"],
                    "default": d == sd.query_devices(kind="input"),
                })
        return result

    def record_blocking(self, duration: float) -> np.ndarray:
        """指定秒数だけ録音して完了を待つ"""
        frames = int(duration * self.sample_rate)
        logger.info("Recording for %s seconds...", duration)
        audio = sd.rec(
            frames,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
        )
        sd.wait()
        logger.info("Recording complete.")
        return audio.flatten()

    def start_recording(self, on_chunk: Callable[[np.ndarray], None] | None = None) -> None:
        """ストリーミング録音を開始する。チャンクごとにコールバックを呼ぶ。"""
        self._frames = []

        def callback(indata, frame_count, time_info, status) -> None:
            if status:
                logger.warning("Audio stream status: %s", status)
            data = indata.copy()
            self._frames.append(data)
            if on_chunk:
                on_chunk(data.flatten())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
            callback=callback,
            blocksize=int(self.sample_rate * CHUNK_DURATION_SEC),
        )
        self._stream.start()

    def stop_recording(self) -> np.ndarray:
        """録音を停止し、蓄積した全音声データを返す"""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if self._frames:
            return np.concatenate(self._frames).flatten()
        return np.array([], dtype=np.float32)

    def save_wav(self, audio: np.ndarray, path: Path | str) -> None:
        """float32音声をint16に変換してWAVファイルに保存する"""
        path = Path(path)
        audio_int16 = (audio * INT16_MAX).astype(np.int16)
        wavfile.write(path, self.sample_rate, audio_int16)
