"""Realtime transcription with VAD (Voice Activity Detection)."""

import tempfile
import threading
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.io import wavfile

from .recorder import MicrophoneRecorder
from .transcriber import WhisperTranscriber


class RealtimeTranscriber:
    """Realtime transcription using VAD-based chunking."""

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
        self._silence_samples = 0
        self._is_speaking = False
        self._running = False
        self._transcription_thread: threading.Thread | None = None
        self._all_text: list[str] = []

    def _process_chunk(self, chunk: np.ndarray):
        """Process audio chunk with simple VAD."""
        amplitude = np.abs(chunk).mean()
        is_speech = amplitude > self.silence_threshold

        if is_speech:
            self._buffer.append(chunk)
            self._silence_samples = 0
            self._is_speaking = True
        else:
            if self._is_speaking:
                self._buffer.append(chunk)
                self._silence_samples += len(chunk)

                # Check if silence duration exceeded
                samples_threshold = int(self.silence_duration * self.recorder.sample_rate)
                if self._silence_samples >= samples_threshold:
                    self._transcribe_buffer()

    def _transcribe_buffer(self):
        """Transcribe accumulated buffer."""
        if not self._buffer:
            return

        audio = np.concatenate(self._buffer).flatten()
        self._buffer = []
        self._is_speaking = False
        self._silence_samples = 0

        # Check minimum length
        min_samples = int(self.min_audio_length * self.recorder.sample_rate)
        if len(audio) < min_samples:
            return

        # Transcribe in separate thread to avoid blocking
        def transcribe():
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = Path(f.name)
                    audio_int16 = (audio * 32767).astype(np.int16)
                    wavfile.write(temp_path, self.recorder.sample_rate, audio_int16)

                result = self.transcriber.transcribe(temp_path)
                temp_path.unlink()

                if result.text.strip():
                    self._all_text.append(result.text.strip())
                    self.on_transcription(result.text.strip())
            except Exception as e:
                print(f"Transcription error: {e}")

        self._transcription_thread = threading.Thread(target=transcribe)
        self._transcription_thread.start()

    def start(self):
        """Start realtime transcription."""
        print(f"Loading model: {self.transcriber.model_name}...")
        # Warm up model
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = Path(f.name)
            silence = np.zeros(16000, dtype=np.int16)
            wavfile.write(temp_path, 16000, silence)
            try:
                self.transcriber.transcribe(temp_path)
            except Exception:
                pass
            temp_path.unlink()

        print("\nRealtime transcription started. Press Ctrl+C to stop.\n")
        print("-" * 50)

        self._running = True
        self._all_text = []
        self.recorder.start_recording(on_chunk=self._process_chunk)

        try:
            while self._running:
                threading.Event().wait(0.1)
        except KeyboardInterrupt:
            pass

        self.stop()

    def stop(self) -> str:
        """Stop transcription and return all text."""
        self._running = False
        self.recorder.stop_recording()

        # Transcribe remaining buffer
        if self._buffer:
            self._transcribe_buffer()

        # Wait for last transcription
        if self._transcription_thread:
            self._transcription_thread.join(timeout=30)

        print("-" * 50)
        return "\n".join(self._all_text)

    def get_all_text(self) -> str:
        """Get all transcribed text."""
        return "\n".join(self._all_text)
