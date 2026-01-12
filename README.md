# mojiokoshi

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Audio transcription & meeting notes CLI tool.

## Features

- **Whisper (large-v3)**: High-accuracy speech recognition
- **Two summarization methods**: Choose based on your needs
- **Apple Silicon optimized**: Runs smoothly on M4 Pro + 48GB RAM

## Choosing a Summarization Method

Two methods are available for creating meeting note summaries. **Choose based on content confidentiality.**

### Local LLM (Ollama) — For Confidential Content

**Data is never sent externally.**

| When to choose | Reason |
|----------------|--------|
| Meetings with confidential or sensitive content | Fully local processing |
| Internal or personal information | No data leak risk |
| No internet connection available | Works offline |
| Want to avoid API costs | Free |

### Claude Code (Slash Commands) — For High-Quality Summaries

**Transcription data is sent to Anthropic's servers.**

| When to choose | Reason |
|----------------|--------|
| General content where external transmission is OK | Higher quality summaries |
| Need higher quality summaries | Claude's superior language understanding |
| Prioritize processing speed | Cloud computing resources |
| Want to save local resources (RAM/GPU) | Runs without Ollama |

## Requirements

> **macOS (Apple Silicon) Only**
>
> This tool uses **mlx-whisper**, which is optimized for Apple Silicon (M1/M2/M3/M4) Metal GPU.
> It does not work on Intel Macs or Linux/Windows.

| Requirement | Description |
|-------------|-------------|
| macOS | Apple Silicon (M1 or later) |
| Python | 3.11 or higher |
| RAM | 16GB+ recommended (when using Ollama) |
| ffmpeg | For audio file processing |
| Ollama | Only when using local LLM |

## Setup

### 1. Install Required Tools

```bash
# If you don't have Homebrew, install it first
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# ffmpeg (audio file processing)
brew install ffmpeg

# uv (Python package manager)
brew install uv
```

### 2. Project Setup

```bash
# Clone the repository
git clone https://github.com/sogengineer/mojiokoshi.git
cd mojiokoshi

# Install dependencies (Whisper model downloads automatically on first run)
uv sync
```

### 3. Ollama Setup (Only for Local LLM)

Skip this step if you're using Claude Code.

```bash
# Install Ollama
brew install ollama

# Start Ollama server
ollama serve

# In another terminal, download LLM models
ollama pull qwen3:14b   # For summarization (~9GB)
ollama pull qwen3:8b    # For correction (~5GB)
```

> **About Whisper Model**
>
> The mlx-whisper model (default: large-v3) downloads automatically on first run.
> No manual installation required.

## Usage

### Using Local LLM (Ollama)

```bash
# Audio file → Meeting notes
make transcribe AUDIO=meeting.m4a OUTPUT=notes.md

# Realtime recording → Meeting notes
make realtime OUTPUT=notes.md

# Existing transcript → Meeting notes
make summarize INPUT=transcript.txt OUTPUT=notes.md
```

### Using Claude Code

Launch Claude Code and run slash commands:

```bash
# Audio file → Meeting notes
/transcribe meeting.m4a notes.md

# Realtime recording → Meeting notes
/realtime notes.md
```

### Transcription Only (No Summary)

```bash
# Transcribe audio file
uv run mojiokoshi file audio.mp3 -o result.txt

# Record and transcribe (Ctrl+C to stop)
uv run mojiokoshi record -o result.txt

# Realtime transcription
uv run mojiokoshi realtime -o result.txt

# List devices
uv run mojiokoshi devices
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `-m, --model` | Whisper model (tiny/base/small/medium/large-v3) | large-v3 |
| `-l, --language` | Language code | ja |
| `-o, --output` | Output file path | auto |
| `--device` | Input device ID | system default |
| `--threshold` | Voice detection threshold (realtime) | 0.01 |
| `--silence` | Silence duration in seconds (realtime) | 1.5 |
| `--duration` | Recording duration in seconds (record) | manual |
| `--save-audio` | Save recording as WAV (record) | - |

## Makefile Options

| Variable | Description | Default |
|----------|-------------|---------|
| MODEL | Whisper model | large-v3 |
| LLM_MODEL | Ollama model | qwen3:14b |

```bash
# Use lighter models for faster processing
make transcribe AUDIO=meeting.m4a OUTPUT=notes.md MODEL=base LLM_MODEL=qwen3:8b
```

## Processing Flow

### Local LLM (Ollama)

```
Audio file / Microphone
       ↓
   Whisper (mlx-whisper)
       ↓
   Transcription text
       ↓
   Ollama (local processing)
       ↓
   Meeting notes (Markdown)
```

### Claude Code

```
Audio file / Microphone
       ↓
   Whisper (mlx-whisper)
       ↓
   Transcription text
       ↓
   Claude (Anthropic API)
       ↓
   Meeting notes (Markdown)
```

## Output Format

```markdown
# Meeting Notes

## Overview
(Meeting purpose and main topic)

## Discussion Points
- Point 1
- Point 2

## Decisions
- Decision 1
- Decision 2

## Action Items
- [ ] Task 1
- [ ] Task 2

## Next Steps
(Future plans)

---

## Full Transcript (Corrected)
(Transcription with typos fixed)
```

## Model Sizes

### Whisper

| Model | Accuracy | Speed | VRAM |
|-------|----------|-------|------|
| tiny | Low | Fastest | ~1GB |
| base | Medium | Fast | ~1GB |
| small | Medium-High | Normal | ~2GB |
| medium | High | Slower | ~5GB |
| large-v3 | Highest | Slow | ~10GB |

### Ollama

| Model | Japanese | Speed | RAM | Purpose |
|-------|----------|-------|-----|---------|
| qwen3:8b | Good | Fast | ~8GB | Correction |
| qwen3:14b | Excellent | Normal | ~16GB | Summary (default) |

## Troubleshooting

### Ollama not starting
```bash
ollama serve
```

### Model not found
```bash
ollama pull qwen3:14b
```

### Microphone not detected
```bash
uv run mojiokoshi devices
```
