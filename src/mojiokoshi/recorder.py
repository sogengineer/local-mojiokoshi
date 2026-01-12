"""Microphone recording module using sounddevice."""

from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd
from scipy.io import wavfile


class MicrophoneRecorder:
    """Record audio from microphone."""

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
        """List available input devices."""
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
        """Record for a fixed duration (blocking)."""
        frames = int(duration * self.sample_rate)
        print(f"Recording for {duration} seconds...")
        audio = sd.rec(
            frames,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
        )
        sd.wait()
        print("Recording complete.")
        return audio.flatten()

    def start_recording(self, on_chunk: Callable[[np.ndarray], None] | None = None):
        """Start continuous recording (non-blocking)."""
        self._frames = []

        def callback(indata, frames, time, status):
            if status:
                print(f"Warning: {status}")
            self._frames.append(indata.copy())
            if on_chunk:
                on_chunk(indata.copy().flatten())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
            callback=callback,
            blocksize=int(self.sample_rate * 0.5),  # 500ms chunks
        )
        self._stream.start()

    def stop_recording(self) -> np.ndarray:
        """Stop recording and return audio data."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if self._frames:
            return np.concatenate(self._frames).flatten()
        return np.array([], dtype=np.float32)

    def save_wav(self, audio: np.ndarray, path: Path | str) -> None:
        """Save audio data as WAV file."""
        path = Path(path)
        audio_int16 = (audio * 32767).astype(np.int16)
        wavfile.write(path, self.sample_rate, audio_int16)
