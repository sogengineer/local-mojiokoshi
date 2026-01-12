# Mojiokoshi - Local Audio Transcription & Summarization
# Usage:
#   make transcribe AUDIO=path/to/audio.m4a OUTPUT=meeting_notes.md
#   make realtime OUTPUT=meeting_notes.md
#   make summarize INPUT=transcript.txt OUTPUT=summary.md

SHELL := /bin/bash
MODEL ?= large-v3
LLM_MODEL ?= qwen3:14b

# Temporary directory
TMP_DIR := .tmp
$(shell mkdir -p $(TMP_DIR))

.PHONY: help setup transcribe realtime summarize clean ollama-start ollama-pull test

help:
	@echo "Mojiokoshi - Local Audio Transcription & Summarization"
	@echo ""
	@echo "Usage:"
	@echo "  make setup                    - Install dependencies and download models"
	@echo "  make transcribe AUDIO=<file> OUTPUT=<file>  - Transcribe audio file and summarize"
	@echo "  make realtime OUTPUT=<file>   - Realtime transcription and summarize"
	@echo "  make summarize INPUT=<file> OUTPUT=<file>   - Summarize existing transcript"
	@echo ""
	@echo "Options:"
	@echo "  MODEL=tiny|base|small|medium|large-v3  (default: large-v3)"
	@echo "  LLM_MODEL=<ollama-model>               (default: qwen3:14b)"
	@echo ""
	@echo "Examples:"
	@echo "  make transcribe AUDIO=meeting.m4a OUTPUT=notes.md"
	@echo "  make realtime OUTPUT=notes.md"
	@echo "  make transcribe AUDIO=meeting.m4a OUTPUT=notes.md MODEL=base"

setup: ollama-pull
	@echo "Setup complete!"

ollama-start:
	@if ! pgrep -x "ollama" > /dev/null; then \
		echo "Starting Ollama server..."; \
		ollama serve > /dev/null 2>&1 & \
		sleep 3; \
	fi

ollama-pull: ollama-start
	@echo "Downloading LLM model: $(LLM_MODEL)"
	ollama pull $(LLM_MODEL)

# Transcribe audio file and summarize
transcribe: ollama-start
ifndef AUDIO
	$(error AUDIO is required. Usage: make transcribe AUDIO=path/to/audio.m4a OUTPUT=notes.md)
endif
ifndef OUTPUT
	$(error OUTPUT is required. Usage: make transcribe AUDIO=path/to/audio.m4a OUTPUT=notes.md)
endif
	@echo "=== Step 1: Transcribing audio ==="
	uv run mojiokoshi file "$(AUDIO)" -m $(MODEL) -o "$(TMP_DIR)/transcript.txt"
	@echo ""
	@echo "=== Step 2: Summarizing with LLM ==="
	uv run python src/mojiokoshi/summarize.py "$(TMP_DIR)/transcript.txt" -o "$(OUTPUT)" -m $(LLM_MODEL)
	@echo ""
	@echo "=== Done! ==="
	@echo "Output: $(OUTPUT)"

# Realtime transcription and summarize
realtime: ollama-start
ifndef OUTPUT
	$(error OUTPUT is required. Usage: make realtime OUTPUT=notes.md)
endif
	@echo "=== Step 1: Realtime transcription ==="
	@echo "Press Ctrl+C to stop recording"
	uv run mojiokoshi realtime -m $(MODEL) -o "$(TMP_DIR)/transcript.txt" || true
	@echo ""
	@echo "=== Step 2: Summarizing with LLM ==="
	uv run python src/mojiokoshi/summarize.py "$(TMP_DIR)/transcript.txt" -o "$(OUTPUT)" -m $(LLM_MODEL)
	@echo ""
	@echo "=== Done! ==="
	@echo "Output: $(OUTPUT)"

# Summarize existing transcript
summarize: ollama-start
ifndef INPUT
	$(error INPUT is required. Usage: make summarize INPUT=transcript.txt OUTPUT=summary.md)
endif
ifndef OUTPUT
	$(error OUTPUT is required. Usage: make summarize INPUT=transcript.txt OUTPUT=summary.md)
endif
	@echo "=== Summarizing with LLM ==="
	uv run python src/mojiokoshi/summarize.py "$(INPUT)" -o "$(OUTPUT)" -m $(LLM_MODEL)
	@echo ""
	@echo "=== Done! ==="
	@echo "Output: $(OUTPUT)"

clean:
	rm -rf $(TMP_DIR)

test:
	uv run pytest tests/ -v
