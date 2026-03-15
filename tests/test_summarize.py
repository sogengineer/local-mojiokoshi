"""Tests for summarize module."""

import json
import urllib.error
import pytest
from unittest.mock import patch, MagicMock
from mojiokoshi.summarize import (
    call_ollama,
    correct_chunk,
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


class TestCallOllama:
    """Tests for call_ollama function."""

    @patch("mojiokoshi.summarize.urllib.request.urlopen")
    def test_call_ollama_success(self, mock_urlopen):
        """Test successful API call."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"message": {"content": "response text"}}
        ).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = call_ollama([{"role": "user", "content": "test"}], "test-model")
        assert result == "response text"

    @patch("mojiokoshi.summarize.urllib.request.urlopen")
    def test_call_ollama_empty_response_raises(self, mock_urlopen):
        """Test that empty response content raises ValueError."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"message": {"content": ""}}
        ).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with pytest.raises(ValueError, match="empty response"):
            call_ollama([{"role": "user", "content": "test"}], "test-model")

    @patch("mojiokoshi.summarize.urllib.request.urlopen")
    def test_call_ollama_retry_on_url_error(self, mock_urlopen):
        """Test retry on URLError then success."""
        success_response = MagicMock()
        success_response.read.return_value = json.dumps(
            {"message": {"content": "ok"}}
        ).encode("utf-8")
        success_response.__enter__ = MagicMock(return_value=success_response)
        success_response.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [
            urllib.error.URLError("connection refused"),
            success_response,
        ]

        result = call_ollama([{"role": "user", "content": "test"}], "test-model")
        assert result == "ok"
        assert mock_urlopen.call_count == 2

    @patch("mojiokoshi.summarize.urllib.request.urlopen")
    def test_call_ollama_raises_after_max_retries(self, mock_urlopen):
        """Test that URLError is raised after all retries exhausted."""
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")

        with pytest.raises(urllib.error.URLError):
            call_ollama([{"role": "user", "content": "test"}], "test-model")
        assert mock_urlopen.call_count == 2  # MAX_RETRIES = 2

    @patch("mojiokoshi.summarize.urllib.request.urlopen")
    def test_call_ollama_retry_on_json_decode_error(self, mock_urlopen):
        """Test retry on JSONDecodeError then success."""
        success_response = MagicMock()
        success_response.read.return_value = json.dumps(
            {"message": {"content": "ok"}}
        ).encode("utf-8")
        success_response.__enter__ = MagicMock(return_value=success_response)
        success_response.__exit__ = MagicMock(return_value=False)

        bad_response = MagicMock()
        bad_response.read.return_value = b"not valid json"
        bad_response.__enter__ = MagicMock(return_value=bad_response)
        bad_response.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [bad_response, success_response]

        result = call_ollama([{"role": "user", "content": "test"}], "test-model")
        assert result == "ok"
        assert mock_urlopen.call_count == 2


class TestCorrectChunk:
    """Tests for correct_chunk function."""

    @patch("mojiokoshi.summarize.call_ollama")
    def test_correct_chunk_with_context(self, mock_call):
        """Test correction with context."""
        mock_call.return_value = json.dumps({"corrected_text": "修正済み"})
        result = correct_chunk("前の文脈", "メインテキスト", "test-model")
        assert result == "修正済み"
        # Verify context is included in the prompt
        call_args = mock_call.call_args[0][0]  # messages
        assert "前の文脈" in call_args[1]["content"]

    @patch("mojiokoshi.summarize.call_ollama")
    def test_correct_chunk_without_context(self, mock_call):
        """Test correction without context."""
        mock_call.return_value = json.dumps({"corrected_text": "修正済み"})
        result = correct_chunk("", "メインテキスト", "test-model")
        assert result == "修正済み"
        call_args = mock_call.call_args[0][0]
        assert "前の文脈" not in call_args[1]["content"]

    @patch("mojiokoshi.summarize.call_ollama")
    def test_correct_chunk_missing_key_fallback(self, mock_call):
        """Test fallback when corrected_text key is missing."""
        mock_call.return_value = json.dumps({"wrong_key": "value"})
        result = correct_chunk("", "元のテキスト", "test-model")
        assert result == "元のテキスト"


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


class TestSummarizeMain:
    """Tests for summarize CLI main function."""

    def test_main_file_not_found(self):
        """Test main exits with error when file not found."""
        from mojiokoshi.summarize import main as summarize_main

        with patch("sys.argv", ["summarize", "/nonexistent/file.txt"]):
            with pytest.raises(SystemExit) as exc_info:
                summarize_main()
            assert exc_info.value.code == 1

    def test_main_empty_file(self, tmp_path):
        """Test main exits with error when file is empty."""
        from mojiokoshi.summarize import main as summarize_main

        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        with patch("sys.argv", ["summarize", str(empty_file)]):
            with pytest.raises(SystemExit) as exc_info:
                summarize_main()
            assert exc_info.value.code == 1


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
