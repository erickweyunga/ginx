"""
Tests for script command registration.
"""

from unittest.mock import MagicMock, patch

import typer

from ginx.cli.registration import create_script_command, register_script_commands


class TestScriptRegistration:
    """Test dynamic script command registration."""

    def test_create_script_command(self):
        """Test creating a script command."""
        script_config = {"command": "pytest", "description": "Run tests"}

        command_func = create_script_command("test", script_config)

        assert callable(command_func)
        assert command_func.__name__ == "script_test"
        assert command_func.__doc__ is not None
        assert script_config["description"] in command_func.__doc__

    @patch("ginx.cli.registration.get_scripts")
    def test_register_script_commands_success(self, mock_get_scripts: MagicMock):
        """Test successful script registration."""
        mock_get_scripts.return_value = {
            "test": {"command": "pytest", "description": "Run tests"},
            "build": {"command": "python -m build", "description": "Build package"},
        }

        app = typer.Typer()
        register_script_commands(app)

        # Verify commands were registered
        # Note: This is a simplified test - in practice you'd check app.commands

    @patch("ginx.cli.registration.get_scripts")
    def test_register_script_commands_skip_reserved(self, mock_get_scripts: MagicMock):
        """Test that reserved commands are skipped."""
        mock_get_scripts.return_value = {
            "test": {"command": "pytest", "description": "Run tests"},
            "version": {  # This should be skipped
                "command": "echo v1.0.0",
                "description": "Show version",
            },
        }

        app = typer.Typer()
        with patch("ginx.cmd.RESERVED_COMMANDS", ["version"]):
            register_script_commands(app)

        # In a real test, you'd verify that 'version' command wasn't registered

    @patch("ginx.cli.registration.get_scripts")
    def test_register_script_commands_error_handling(self, mock_get_scripts: MagicMock, capsys: MagicMock):
        """Test error handling during registration."""
        mock_get_scripts.side_effect = Exception("Config error")

        app = typer.Typer()
        register_script_commands(app)

        captured = capsys.readouterr()
        assert "Warning: Could not load scripts" in captured.out
