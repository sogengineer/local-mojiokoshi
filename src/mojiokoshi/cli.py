"""CLI entry point for mojiokoshi."""

import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from .recorder import MicrophoneRecorder
from .realtime import RealtimeTranscriber
from .transcriber import WhisperTranscriber


def cmd_file(args):
    """Transcribe audio file."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    print(f"Loading model: {args.model}")
    transcriber = WhisperTranscriber(model_name=args.model, language=args.language)

    print(f"Transcribing: {input_path}")
    result = transcriber.transcribe(input_path)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(".txt")

    output_path.write_text(result.text, encoding="utf-8")
    print(f"\nSaved to: {output_path}")
    print(f"\n--- Result ---\n{result.text}")


def cmd_record(args):
    """Record and transcribe."""
    recorder = MicrophoneRecorder(device=args.device)

    # Generate output filename
    if args.output:
        output_base = Path(args.output).stem
        output_dir = Path(args.output).parent
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_base = f"recording_{timestamp}"
        output_dir = Path(".")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Record
    if args.duration:
        audio = recorder.record_blocking(args.duration)
    else:
        print("Recording... Press Ctrl+C to stop")
        recorder.start_recording()
        try:
            while True:
                pass
        except KeyboardInterrupt:
            pass
        audio = recorder.stop_recording()
        print("\nRecording stopped.")

    if len(audio) == 0:
        print("Error: No audio recorded")
        sys.exit(1)

    # Save audio if requested
    if args.save_audio:
        wav_path = output_dir / f"{output_base}.wav"
        recorder.save_wav(audio, wav_path)
        print(f"Audio saved: {wav_path}")

    # Transcribe
    print(f"\nLoading model: {args.model}")
    transcriber = WhisperTranscriber(model_name=args.model, language=args.language)

    # Save to temp file for transcription
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = Path(f.name)
        recorder.save_wav(audio, temp_path)

    print("Transcribing...")
    result = transcriber.transcribe(temp_path)
    temp_path.unlink()

    # Save result
    txt_path = output_dir / f"{output_base}.txt"
    txt_path.write_text(result.text, encoding="utf-8")

    print(f"\nSaved to: {txt_path}")
    print(f"\n--- Result ---\n{result.text}")


def cmd_realtime(args):
    """Realtime transcription."""
    # Generate output filename
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"realtime_{timestamp}.txt")

    def on_text(text: str):
        print(f">> {text}")

    rt = RealtimeTranscriber(
        model_name=args.model,
        language=args.language,
        silence_threshold=args.threshold,
        silence_duration=args.silence,
        on_transcription=on_text,
        device=args.device,
    )

    try:
        rt.start()
    except KeyboardInterrupt:
        pass

    all_text = rt.get_all_text()
    if all_text:
        output_path.write_text(all_text, encoding="utf-8")
        print(f"\nSaved to: {output_path}")


def cmd_devices(args):
    """List available audio devices."""
    devices = MicrophoneRecorder.list_devices()
    print("\nAvailable input devices:\n")
    for d in devices:
        default = " (default)" if d["default"] else ""
        print(f"  [{d['id']}] {d['name']}{default}")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="mojiokoshi",
        description="Audio transcription CLI tool using Whisper",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # file command
    file_parser = subparsers.add_parser("file", help="Transcribe audio file")
    file_parser.add_argument("input", help="Input audio file path")
    file_parser.add_argument("-o", "--output", help="Output text file path")
    file_parser.add_argument(
        "-m", "--model",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        default="large-v3",
        help="Whisper model size (default: large-v3)",
    )
    file_parser.add_argument(
        "-l", "--language",
        default="ja",
        help="Language code (default: ja)",
    )
    file_parser.set_defaults(func=cmd_file)

    # record command
    record_parser = subparsers.add_parser("record", help="Record and transcribe")
    record_parser.add_argument("-o", "--output", help="Output file base name")
    record_parser.add_argument(
        "-d", "--duration",
        type=float,
        help="Recording duration in seconds (default: manual stop)",
    )
    record_parser.add_argument(
        "-m", "--model",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        default="large-v3",
        help="Whisper model size (default: large-v3)",
    )
    record_parser.add_argument(
        "-l", "--language",
        default="ja",
        help="Language code (default: ja)",
    )
    record_parser.add_argument(
        "--device",
        type=int,
        help="Input device ID",
    )
    record_parser.add_argument(
        "--save-audio",
        action="store_true",
        help="Save recorded audio as WAV file",
    )
    record_parser.set_defaults(func=cmd_record)

    # realtime command
    realtime_parser = subparsers.add_parser("realtime", help="Realtime transcription")
    realtime_parser.add_argument("-o", "--output", help="Output text file path")
    realtime_parser.add_argument(
        "-m", "--model",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        default="large-v3",
        help="Whisper model size (default: large-v3)",
    )
    realtime_parser.add_argument(
        "-l", "--language",
        default="ja",
        help="Language code (default: ja)",
    )
    realtime_parser.add_argument(
        "--device",
        type=int,
        help="Input device ID",
    )
    realtime_parser.add_argument(
        "--threshold",
        type=float,
        default=0.01,
        help="Voice activity threshold (default: 0.01)",
    )
    realtime_parser.add_argument(
        "--silence",
        type=float,
        default=1.5,
        help="Silence duration to trigger transcription (default: 1.5s)",
    )
    realtime_parser.set_defaults(func=cmd_realtime)

    # devices command
    devices_parser = subparsers.add_parser("devices", help="List audio devices")
    devices_parser.set_defaults(func=cmd_devices)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
