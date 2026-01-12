"""Tests for summarize module."""

import json
import pytest
from unittest.mock import patch, MagicMock
from mojiokoshi.summarize import (
    summarize,
    to_markdown,
    MeetingNotes,
    CorrectedChunk,
    CORRECTION_PROMPT,
    SUMMARY_PROMPT,
    OLLAMA_API,
    split_into_chunks_with_context,
)


class TestMeetingNotes:
    """Tests for MeetingNotes Pydantic model."""

    def test_meeting_notes_schema(self):
        """Test MeetingNotes schema structure."""
        notes = MeetingNotes(
            summary="テスト概要",
            key_points=["ポイント1", "ポイント2"],
            discussion_topics=["トピック1"],
            decisions=["決定事項1"],
            action_items=["タスク1"],
            notable_quotes=["「引用1」"],
        )
        assert notes.summary == "テスト概要"
        assert len(notes.key_points) == 2
        assert len(notes.discussion_topics) == 1
        assert len(notes.decisions) == 1
        assert len(notes.action_items) == 1
        assert len(notes.notable_quotes) == 1

    def test_meeting_notes_json_schema(self):
        """Test MeetingNotes generates valid JSON schema."""
        schema = MeetingNotes.model_json_schema()
        assert "properties" in schema
        assert "summary" in schema["properties"]
        assert "key_points" in schema["properties"]
        assert "discussion_topics" in schema["properties"]
        assert "decisions" in schema["properties"]
        assert "action_items" in schema["properties"]
        assert "notable_quotes" in schema["properties"]

    def test_corrected_chunk_schema(self):
        """Test CorrectedChunk schema structure."""
        chunk = CorrectedChunk(corrected_text="修正済みテキスト")
        assert chunk.corrected_text == "修正済みテキスト"


class TestToMarkdown:
    """Tests for to_markdown function."""

    def test_to_markdown_basic(self):
        """Test basic markdown conversion."""
        notes = MeetingNotes(
            summary="これはテストです。",
            key_points=["ポイント1", "ポイント2"],
            discussion_topics=["トピック1"],
            decisions=["決定事項1"],
            action_items=["タスク1"],
            notable_quotes=["「引用1」"],
        )
        result = to_markdown(notes, "修正済みテキスト")

        assert "# 議事録" in result
        assert "## 概要" in result
        assert "これはテストです。" in result
        assert "## 主なポイント" in result
        assert "- ポイント1" in result
        assert "## 議論されたトピック" in result
        assert "## 決定事項・結論" in result
        assert "## アクションアイテム" in result
        assert "- [ ] タスク1" in result
        assert "## 印象的な発言" in result
        assert "## 文字起こし全文（修正済み）" in result

    def test_to_markdown_empty_lists(self):
        """Test markdown conversion with empty lists."""
        notes = MeetingNotes(
            summary="概要",
            key_points=["ポイント"],
            discussion_topics=[],
            decisions=[],
            action_items=[],
            notable_quotes=[],
        )
        result = to_markdown(notes, "テキスト")

        assert "- なし" in result


class TestSummarize:
    """Tests for summarize function."""

    def test_ollama_api_url(self):
        """Test Ollama API URL is correct."""
        assert OLLAMA_API == "http://localhost:11434/api/chat"

    def test_correction_prompt_contains_key_instructions(self):
        """Test correction prompt contains important instructions."""
        assert "校正" in CORRECTION_PROMPT
        assert "誤字" in CORRECTION_PROMPT
        assert "フィラー" in CORRECTION_PROMPT
        assert "修正対象" in CORRECTION_PROMPT

    def test_summary_prompt_contains_key_instructions(self):
        """Test summary prompt contains important instructions."""
        assert "議事録" in SUMMARY_PROMPT
        assert "JSON" in SUMMARY_PROMPT
        assert "summary" in SUMMARY_PROMPT
        assert "key_points" in SUMMARY_PROMPT

    @patch("mojiokoshi.summarize.urllib.request.urlopen")
    def test_summarize_success(self, mock_urlopen):
        """Test successful summarization with 2-stage processing."""
        # Mock responses for correction (stage 1) and summary (stage 2)
        correction_response = {"corrected_text": "修正テキスト"}
        summary_response = {
            "summary": "テスト概要",
            "key_points": ["ポイント1"],
            "discussion_topics": ["トピック1"],
            "decisions": ["決定1"],
            "action_items": ["タスク1"],
            "notable_quotes": ["「引用1」"],
        }

        mock_response = MagicMock()
        # First call returns correction, second returns summary
        mock_response.read.side_effect = [
            json.dumps({"message": {"content": json.dumps(correction_response)}}).encode("utf-8"),
            json.dumps({"message": {"content": json.dumps(summary_response)}}).encode("utf-8"),
        ]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = summarize("テストテキスト", model="qwen3:14b")

        assert "# 議事録" in result
        assert "テスト概要" in result
        # 2 calls: 1 for correction (short text = 1 chunk), 1 for summary
        assert mock_urlopen.call_count == 2

    @patch("mojiokoshi.summarize.urllib.request.urlopen")
    def test_summarize_uses_different_models(self, mock_urlopen):
        """Test that correction and summary use different models."""
        correction_response = {"corrected_text": "修正テキスト"}
        summary_response = {
            "summary": "概要",
            "key_points": ["ポイント"],
            "discussion_topics": [],
            "decisions": [],
            "action_items": [],
            "notable_quotes": [],
        }

        mock_response = MagicMock()
        mock_response.read.side_effect = [
            json.dumps({"message": {"content": json.dumps(correction_response)}}).encode("utf-8"),
            json.dumps({"message": {"content": json.dumps(summary_response)}}).encode("utf-8"),
        ]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        summarize("test", model="qwen3:14b", correction_model="qwen3:8b")

        # Check first call uses correction model
        first_call = mock_urlopen.call_args_list[0]
        first_payload = json.loads(first_call[0][0].data.decode("utf-8"))
        assert first_payload["model"] == "qwen3:8b"

        # Check second call uses summary model
        second_call = mock_urlopen.call_args_list[1]
        second_payload = json.loads(second_call[0][0].data.decode("utf-8"))
        assert second_payload["model"] == "qwen3:14b"


class TestChunking:
    """Tests for text chunking functionality."""

    def test_split_short_text(self):
        """Test splitting text shorter than chunk size."""
        text = "短いテキスト"
        chunks = split_into_chunks_with_context(text, chunk_size=100, context_size=20)
        assert len(chunks) == 1
        assert chunks[0] == ("", "短いテキスト")

    def test_split_long_text(self):
        """Test splitting text into multiple chunks."""
        text = "A" * 100
        chunks = split_into_chunks_with_context(text, chunk_size=30, context_size=10)
        assert len(chunks) == 4  # 100 / 30 = 3.33 -> 4 chunks

    def test_context_from_previous_chunk(self):
        """Test that context is taken from previous chunk."""
        text = "前の文脈" + "メイン部分"  # 4 + 5 = 9 chars
        chunks = split_into_chunks_with_context(text, chunk_size=5, context_size=4)
        assert len(chunks) == 2
        # First chunk has no context
        assert chunks[0] == ("", "前の文脈メ")
        # Second chunk has context from first
        assert chunks[1][0] == "の文脈メ"  # context
        assert chunks[1][1] == "イン部分"  # main text


class TestPrompts:
    """Tests for prompt content."""

    def test_correction_prompt_fields(self):
        """Test that correction prompt includes key fields."""
        assert "修正対象" in CORRECTION_PROMPT
        assert "前の文脈" in CORRECTION_PROMPT
        assert "要約せず" in CORRECTION_PROMPT

    def test_summary_prompt_fields(self):
        """Test that summary prompt includes field instructions."""
        assert "summary" in SUMMARY_PROMPT
        assert "key_points" in SUMMARY_PROMPT
        assert "discussion_topics" in SUMMARY_PROMPT
        assert "decisions" in SUMMARY_PROMPT
        assert "action_items" in SUMMARY_PROMPT
        assert "notable_quotes" in SUMMARY_PROMPT
