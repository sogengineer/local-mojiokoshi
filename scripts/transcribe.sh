#!/bin/bash
# Transcribe audio file and create summary
# Usage: ./scripts/transcribe.sh <audio_file> <output_file> [model]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TMP_DIR="$PROJECT_DIR/.tmp"

AUDIO_FILE="$1"
OUTPUT_FILE="$2"
WHISPER_MODEL="${3:-large-v3}"
LLM_MODEL="${4:-qwen2.5:14b}"

if [ -z "$AUDIO_FILE" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <audio_file> <output_file> [whisper_model] [llm_model]"
    echo ""
    echo "Arguments:"
    echo "  audio_file     Input audio file (m4a, mp3, wav, etc.)"
    echo "  output_file    Output markdown file"
    echo "  whisper_model  Whisper model (default: large-v3)"
    echo "  llm_model      Ollama model (default: qwen2.5:14b)"
    echo ""
    echo "Example:"
    echo "  $0 meeting.m4a notes.md"
    echo "  $0 meeting.m4a notes.md base qwen2.5:7b"
    exit 1
fi

mkdir -p "$TMP_DIR"

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama server..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

echo "=== Step 1: Transcribing audio ==="
echo "Audio: $AUDIO_FILE"
echo "Model: $WHISPER_MODEL"
cd "$PROJECT_DIR"
uv run mojiokoshi file "$AUDIO_FILE" -m "$WHISPER_MODEL" -o "$TMP_DIR/transcript.txt"

echo ""
echo "=== Step 2: Summarizing with LLM ==="
echo "Model: $LLM_MODEL"
uv run python src/mojiokoshi/summarize.py "$TMP_DIR/transcript.txt" -o "$OUTPUT_FILE" -m "$LLM_MODEL"

echo ""
echo "=== Done! ==="
echo "Output: $OUTPUT_FILE"
