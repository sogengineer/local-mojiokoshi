#!/bin/bash
# Realtime transcription and create summary
# Usage: ./scripts/realtime.sh <output_file> [model]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TMP_DIR="$PROJECT_DIR/.tmp"

OUTPUT_FILE="$1"
WHISPER_MODEL="${2:-large-v3}"
LLM_MODEL="${3:-qwen2.5:14b}"

if [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <output_file> [whisper_model] [llm_model]"
    echo ""
    echo "Arguments:"
    echo "  output_file    Output markdown file"
    echo "  whisper_model  Whisper model (default: large-v3)"
    echo "  llm_model      Ollama model (default: qwen2.5:14b)"
    echo ""
    echo "Example:"
    echo "  $0 notes.md"
    echo "  $0 notes.md base qwen2.5:7b"
    exit 1
fi

mkdir -p "$TMP_DIR"

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama server..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

echo "=== Step 1: Realtime transcription ==="
echo "Model: $WHISPER_MODEL"
echo "Press Ctrl+C to stop recording"
echo ""
cd "$PROJECT_DIR"
uv run mojiokoshi realtime -m "$WHISPER_MODEL" -o "$TMP_DIR/transcript.txt" || true

echo ""
echo "=== Step 2: Summarizing with LLM ==="
echo "Model: $LLM_MODEL"
uv run python src/mojiokoshi/summarize.py "$TMP_DIR/transcript.txt" -o "$OUTPUT_FILE" -m "$LLM_MODEL"

echo ""
echo "=== Done! ==="
echo "Output: $OUTPUT_FILE"
