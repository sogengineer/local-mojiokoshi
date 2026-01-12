# mojiokoshi

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

音声文字起こし & 議事録作成CLIツール。

## 特徴

- **Whisper (large-v3)**: 高精度な音声認識
- **2つのサマリ作成方式**: 用途に応じて選択可能
- **Apple Silicon最適化**: M4 Pro + 48GB RAMで快適動作

## サマリ作成方法の選択

議事録サマリは2つの方法で作成できます。**内容の機密性**に応じて選択してください。

### ローカルLLM（Ollama）— 機密情報向け

**データは外部に一切送信されません。**

| こんな時に選ぶ | 理由 |
|---------------|------|
| 機密情報・センシティブな内容を含む会議 | 完全ローカル処理 |
| 社内の未公開情報や個人情報を扱う | 情報漏洩リスクなし |
| インターネット接続がない環境 | オフライン動作可能 |
| API料金をかけたくない | 無料 |

### Claude Code（スラッシュコマンド）— 高品質サマリ向け

**文字起こしデータはAnthropicのサーバーに送信されます。**

| こんな時に選ぶ | 理由 |
|---------------|------|
| 一般的な内容で外部送信が問題ない | 高品質なサマリ |
| より高品質なサマリが必要 | Claudeの高い言語理解能力 |
| 処理速度を優先したい | クラウドの計算リソース活用 |
| ローカルのリソース（RAM/GPU）を節約したい | Ollama不要で軽量動作 |

## 動作環境

> **macOS (Apple Silicon) 専用**
>
> このツールは **mlx-whisper** を使用しており、Apple Silicon (M1/M2/M3/M4) の Metal GPU に最適化されています。
> Intel Mac や Linux/Windows では動作しません。

| 要件 | 説明 |
|-----|------|
| macOS | Apple Silicon (M1以降) |
| Python | 3.11 以上 |
| RAM | 16GB 以上推奨（Ollama使用時） |
| ffmpeg | 音声ファイル処理用 |
| Ollama | ローカルLLM使用時のみ |

## セットアップ

### 1. 必須ツールのインストール

```bash
# Homebrew がない場合は先にインストール
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# ffmpeg（音声ファイル処理）
brew install ffmpeg

# uv（Pythonパッケージマネージャー）
brew install uv
```

### 2. プロジェクトのセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/sogengineer/mojiokoshi.git
cd mojiokoshi

# 依存関係をインストール（Whisperモデルは初回実行時に自動ダウンロード）
uv sync
```

### 3. Ollama のセットアップ（ローカルLLM使用時のみ）

Claude Code を使う場合はこの手順は不要です。

```bash
# Ollamaをインストール
brew install ollama

# Ollamaサーバーを起動
ollama serve

# 別のターミナルでLLMモデルをダウンロード
ollama pull qwen3:14b   # サマリ用（約9GB）
ollama pull qwen3:8b    # 校正用（約5GB）
```

> **Whisperモデルについて**
>
> mlx-whisper のモデル（デフォルト: large-v3）は初回実行時に自動的にダウンロードされます。
> 手動でのインストールは不要です。

## 使い方

### ローカルLLM（Ollama）を使う場合

```bash
# 音声ファイル → 議事録
make transcribe AUDIO=meeting.m4a OUTPUT=notes.md

# リアルタイム録音 → 議事録
make realtime OUTPUT=notes.md

# 既存の文字起こし → 議事録
make summarize INPUT=transcript.txt OUTPUT=notes.md
```

### Claude Code を使う場合

Claude Code を起動して、スラッシュコマンドを実行：

```bash
# 音声ファイル → 議事録
/transcribe meeting.m4a notes.md

# リアルタイム録音 → 議事録
/realtime notes.md
```

### 文字起こしのみ（サマリなし）

```bash
# 音声ファイルを文字起こし
uv run mojiokoshi file audio.mp3 -o result.txt

# 録音して文字起こし（Ctrl+C で停止）
uv run mojiokoshi record -o result.txt

# リアルタイム文字起こし
uv run mojiokoshi realtime -o result.txt

# デバイス確認
uv run mojiokoshi devices
```

## オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `-m, --model` | Whisperモデル (tiny/base/small/medium/large-v3) | large-v3 |
| `-l, --language` | 言語コード | ja |
| `-o, --output` | 出力ファイルパス | 自動生成 |
| `--device` | 入力デバイスID | システムデフォルト |
| `--threshold` | 音声検出の閾値（realtime用） | 0.01 |
| `--silence` | 無音継続時間・秒（realtime用） | 1.5 |
| `--duration` | 録音時間・秒（record用） | 手動停止 |
| `--save-audio` | 録音音声をWAV保存（record用） | - |

## Makefileオプション

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| MODEL | Whisperモデル | large-v3 |
| LLM_MODEL | Ollamaモデル | qwen3:14b |

```bash
# 軽量モデルで高速処理
make transcribe AUDIO=meeting.m4a OUTPUT=notes.md MODEL=base LLM_MODEL=qwen3:8b
```

## 処理フロー

### ローカルLLM（Ollama）

```
音声ファイル/マイク
       ↓
   Whisper (mlx-whisper)
       ↓
   文字起こしテキスト
       ↓
   Ollama (ローカル処理)
       ↓
   議事録 (Markdown)
```

### Claude Code

```
音声ファイル/マイク
       ↓
   Whisper (mlx-whisper)
       ↓
   文字起こしテキスト
       ↓
   Claude (Anthropic API)
       ↓
   議事録 (Markdown)
```

## 出力形式

```markdown
# 議事録

## 概要
（会議の目的・主題）

## 議論のポイント
- ポイント1
- ポイント2

## 決定事項
- 決定1
- 決定2

## アクションアイテム
- [ ] タスク1
- [ ] タスク2

## 次回に向けて
（次のステップ）

---

## 文字起こし全文（修正済み）
（誤字修正後のテキスト）
```

## モデルサイズ

### Whisper

| モデル | 精度 | 速度 | VRAM |
|--------|------|------|------|
| tiny | 低 | 最速 | ~1GB |
| base | 中 | 速い | ~1GB |
| small | 中高 | 普通 | ~2GB |
| medium | 高 | やや遅い | ~5GB |
| large-v3 | 最高 | 遅い | ~10GB |

### Ollama

| モデル | 日本語 | 速度 | RAM | 用途 |
|--------|--------|------|-----|------|
| qwen3:8b | 良好 | 速い | ~8GB | 校正用 |
| qwen3:14b | 優秀 | 普通 | ~16GB | サマリ用（デフォルト） |

## トラブルシューティング

### Ollamaが起動しない
```bash
ollama serve
```

### モデルがない
```bash
ollama pull qwen3:14b
```

### マイクが認識されない
```bash
uv run mojiokoshi devices
```
