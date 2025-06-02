"""
Tests for command parsing functionality.
"""

import pytest
import typer

from ginx.utils import parse_command_and_extra


class TestCommandParsing:
    """Test command parsing with variable support."""

    def test_command_with_variables(self):
        """Test parsing command with variables."""
        command = "git commit -m ${message:string}"
        full_cmd, display = parse_command_and_extra(command, "fix: bug", needs_shell=False)

        assert isinstance(full_cmd, list)
        assert full_cmd == ["git", "commit", "-m", "fix: bug"]  # Split removes quotes
        assert display == 'git commit -m "fix: bug"'  # Display keeps processed string

    def test_command_with_variables_shell(self):
        """Test parsing command with variables for shell execution."""
        command = "git commit -m ${message:string}"
        full_cmd, display = parse_command_and_extra(command, "fix: bug", needs_shell=True)

        assert isinstance(full_cmd, str)
        assert full_cmd == 'git commit -m "fix: bug"'
        assert display == 'git commit -m "fix: bug"'

    def test_command_without_variables(self):
        """Test parsing regular command without variables."""
        command = "pytest"
        full_cmd, display = parse_command_and_extra(command, "--verbose", needs_shell=False)

        assert full_cmd == ["pytest", "--verbose"]
        assert display == "pytest --verbose"

    def test_command_without_variables_shell(self):
        """Test parsing regular command for shell execution."""
        command = "pytest"
        full_cmd, _ = parse_command_and_extra(command, "--verbose", needs_shell=True)

        assert full_cmd == "pytest --verbose"

    def test_command_no_extra(self):
        """Test command without extra arguments."""
        command = "pytest"
        full_cmd, display = parse_command_and_extra(command, "", needs_shell=False)

        assert full_cmd == ["pytest"]
        assert display == "pytest"

    def test_command_with_variables_no_extra(self):
        """Test command with variables but no input raises error."""
        command = "git commit -m ${message:string}"
        with pytest.raises(typer.Exit):
            parse_command_and_extra(command, "", needs_shell=False)

    def test_complex_shell_command(self):
        """Test complex shell command with operators."""
        command = "echo ${message:string} && ls"
        full_cmd, _ = parse_command_and_extra(command, "hello", needs_shell=True)

        assert full_cmd == 'echo "hello" && ls'

    def test_invalid_shell_syntax(self):
        """Test handling invalid shell syntax."""
        command = "echo 'unclosed quote"
        with pytest.raises(typer.Exit):
            parse_command_and_extra(command, "", needs_shell=False)
