"""Summarize transcription using local LLM (Ollama) with structured output."""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

from pydantic import BaseModel


OLLAMA_API = "http://localhost:11434/api/chat"

# Chunking settings
CHUNK_SIZE = 4000  # characters per chunk
CONTEXT_SIZE = 300  # context from previous chunk (not included in output)


class CorrectedChunk(BaseModel):
    """Schema for corrected text chunk."""
    corrected_text: str


class MeetingNotes(BaseModel):
    """Structured meeting notes schema."""
    summary: str  # 概要（3-5文で詳細に）
    key_points: list[str]  # 主なポイント（5-8個）
    discussion_topics: list[str]  # 議論されたトピック
    decisions: list[str]  # 決定事項・結論
    action_items: list[str]  # アクションアイテム
    notable_quotes: list[str]  # 印象的な発言


CORRECTION_PROMPT = """あなたは日本語校正AIです。

【タスク】
「===修正対象===」の部分のみを修正して出力してください。
「===前の文脈===」は文脈理解のためだけに使用し、出力には含めないでください。

【修正ルール】
1. 誤字脱字を修正する
2. 同音異義語を文脈に合わせて修正する
3. フィラー（えー、あのー、まあ、ですね、なんか等）を削除する
4. 文意は変えずに読みやすくする
5. 句読点を適切に追加する
6. 改行を適切に入れて読みやすくする

【重要】
- 内容を要約せず、修正対象の全文を出力すること
- 前の文脈は出力に含めないこと"""


SUMMARY_PROMPT = """あなたは議事録作成AIです。修正済みの文字起こしテキストから詳細な要約をJSON形式で生成してください。

【出力ルール】
1. summary: 3-5文で内容を詳細に要約。話者の主張、背景、結論を含める
2. key_points: 主なポイントを5-8個リストアップ。具体的なエピソードや数字も含める
3. discussion_topics: 議論されたトピックやテーマを3-5個
4. decisions: 決定事項や結論をリストアップ（なければ空リスト）
5. action_items: アクションアイテムをリストアップ（なければ空リスト）
6. notable_quotes: 印象的な発言や名言を2-4個（「」で囲んで引用）

【注意】
- 簡潔すぎる要約は避け、聞いていない人にも内容が伝わるように詳細に書く
- 具体的な固有名詞、数字、エピソードを積極的に含める"""


def split_into_chunks_with_context(text: str, chunk_size: int = CHUNK_SIZE, context_size: int = CONTEXT_SIZE) -> list[tuple[str, str]]:
    """Split text into chunks with context from previous chunk.

    Returns list of (context, main_text) tuples.
    - context: Text from previous chunk for understanding (not to be included in output)
    - main_text: Text to be corrected and output
    """
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # Get context from before this chunk (if not first chunk)
        if start > 0:
            context_start = max(0, start - context_size)
            context = text[context_start:start]
        else:
            context = ""

        main_text = text[start:end]
        chunks.append((context, main_text))

        start = end

    return chunks


def call_ollama(messages: list, model: str, schema: type[BaseModel] | None = None, timeout: int = 300) -> str:
    """Call Ollama API and return response content."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 8192,
        },
    }

    if schema:
        payload["format"] = schema.model_json_schema()

    req = urllib.request.Request(
        OLLAMA_API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
        return result.get("message", {}).get("content", "")


def correct_chunk(context: str, main_text: str, model: str) -> str:
    """Correct a single chunk of text with context."""
    if context:
        user_content = f"===前の文脈===\n{context}\n\n===修正対象===\n{main_text}"
    else:
        user_content = f"===修正対象===\n{main_text}"

    messages = [
        {"role": "system", "content": CORRECTION_PROMPT},
        {"role": "user", "content": user_content},
    ]

    content = call_ollama(messages, model, schema=CorrectedChunk)
    data = json.loads(content)
    return data.get("corrected_text", main_text)


def correct_full_transcript(text: str, model: str) -> str:
    """Correct the full transcript by processing chunks with context."""
    chunks = split_into_chunks_with_context(text)
    total_chunks = len(chunks)

    print(f"  Correcting {total_chunks} chunks...")

    corrected_parts = []

    for i, (context, main_text) in enumerate(chunks):
        print(f"  Processing chunk {i + 1}/{total_chunks}...", end=" ", flush=True)
        corrected = correct_chunk(context, main_text, model)
        corrected_parts.append(corrected)
        print("done")

    return "\n\n".join(corrected_parts)


def summarize_corrected_text(corrected_text: str, model: str) -> MeetingNotes:
    """Generate detailed summary from corrected text."""
    messages = [
        {"role": "system", "content": SUMMARY_PROMPT},
        {"role": "user", "content": f"以下の修正済み文字起こしから詳細な議事録を作成してください：\n\n{corrected_text}"},
    ]

    content = call_ollama(messages, model, schema=MeetingNotes, timeout=600)
    data = json.loads(content)
    return MeetingNotes(**data)


def to_markdown(notes: MeetingNotes, corrected_transcript: str) -> str:
    """Convert MeetingNotes to Markdown format."""
    key_points = "\n".join(f"- {p}" for p in notes.key_points)
    discussion_topics = "\n".join(f"- {t}" for t in notes.discussion_topics) if notes.discussion_topics else "- なし"
    decisions = "\n".join(f"- {d}" for d in notes.decisions) if notes.decisions else "- なし"
    action_items = "\n".join(f"- [ ] {a}" for a in notes.action_items) if notes.action_items else "- [ ] なし"
    notable_quotes = "\n".join(f"- {q}" for q in notes.notable_quotes) if notes.notable_quotes else "- なし"

    return f"""# 議事録

## 概要
{notes.summary}

## 主なポイント
{key_points}

## 議論されたトピック
{discussion_topics}

## 決定事項・結論
{decisions}

## アクションアイテム
{action_items}

## 印象的な発言
{notable_quotes}

---

## 文字起こし全文（修正済み）
{corrected_transcript}
"""


def summarize(
    text: str,
    model: str = "qwen3:14b",
    correction_model: str | None = None,
) -> str:
    """Summarize text using 2-stage processing: correct then summarize.

    Args:
        text: The transcript text to process
        model: Model for summarization (quality-focused)
        correction_model: Model for text correction (speed-focused). Defaults to model if not specified.
    """
    correction_model = correction_model or model

    # Stage 1: Correct the full transcript (use faster model)
    print(f"Stage 1: Correcting transcript (model: {correction_model})...")
    corrected_text = correct_full_transcript(text, correction_model)

    # Stage 2: Generate summary from corrected text (use quality model)
    print(f"\nStage 2: Generating detailed summary (model: {model})...")
    notes = summarize_corrected_text(corrected_text, model)

    return to_markdown(notes, corrected_text)


def main():
    parser = argparse.ArgumentParser(description="Summarize transcription using local LLM")
    parser.add_argument("input", help="Input transcription file")
    parser.add_argument("-o", "--output", help="Output markdown file")
    parser.add_argument(
        "-m", "--model",
        default="qwen3:14b",
        help="Model for summarization (default: qwen3:14b)",
    )
    parser.add_argument(
        "-c", "--correction-model",
        default="qwen3:8b",
        help="Model for text correction, faster (default: qwen3:8b)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    text = input_path.read_text(encoding="utf-8")

    if not text.strip():
        print("Error: Input file is empty", file=sys.stderr)
        sys.exit(1)

    print(f"Summary model: {args.model}")
    print(f"Correction model: {args.correction_model}")
    print(f"Input length: {len(text)} characters\n")

    try:
        result = summarize(text, args.model, args.correction_model)
    except urllib.error.URLError as e:
        print(f"Error: Ollama server not running? {e}", file=sys.stderr)
        print("Start with: ollama serve", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON response: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(".md")

    output_path.write_text(result, encoding="utf-8")
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
