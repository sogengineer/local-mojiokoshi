"""Tests for CLI module."""

import pytest
from unittest.mock import patch, MagicMock
from mojiokoshi.cli import main


class TestCLI:
    """Tests for CLI commands."""

    def test_help_exits_zero(self):
        """Test --help exits with code 0."""
        with patch("sys.argv", ["mojiokoshi", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_file_command_requires_input(self):
        """Test file command requires input argument."""
        with patch("sys.argv", ["mojiokoshi", "file"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code != 0

    def test_file_command_with_nonexistent_file(self):
        """Test file command with non-existent file."""
        with patch("sys.argv", ["mojiokoshi", "file", "/nonexistent/file.mp3"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("mojiokoshi.cli.MicrophoneRecorder")
    def test_devices_command(self, mock_recorder_class):
        """Test devices command lists devices."""
        mock_recorder_class.list_devices.return_value = [
            {"id": 0, "name": "Test Mic", "channels": 1, "default": True}
        ]

        with patch("sys.argv", ["mojiokoshi", "devices"]):
            # Should not raise
            main()

        mock_recorder_class.list_devices.assert_called_once()


class TestCLIArguments:
    """Tests for CLI argument parsing."""

    def test_file_model_choices(self):
        """Test file command accepts valid model choices."""
        valid_models = ["tiny", "base", "small", "medium", "large-v3"]

        for model in valid_models:
            with patch("sys.argv", ["mojiokoshi", "file", "test.mp3", "-m", model]):
                # Should fail at file not found, not argument parsing
                with pytest.raises(SystemExit) as exc_info:
                    main()
                # Exit code 1 means file not found (not argument error which is 2)
                assert exc_info.value.code == 1

    def test_file_invalid_model_rejected(self):
        """Test file command rejects invalid model."""
        with patch("sys.argv", ["mojiokoshi", "file", "test.mp3", "-m", "invalid"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # argparse exits with 2 for invalid arguments
            assert exc_info.value.code == 2

    def test_record_duration_option(self):
        """Test record command accepts duration option."""
        with patch("sys.argv", ["mojiokoshi", "record", "-d", "5"]):
            with patch("mojiokoshi.cli.MicrophoneRecorder") as mock:
                mock_instance = MagicMock()
                mock_instance.record_blocking.return_value = MagicMock()
                mock.return_value = mock_instance

                # Will fail at transcription, but argument parsing should work
                with pytest.raises((SystemExit, Exception)):
                    main()
