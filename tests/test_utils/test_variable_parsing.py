"""
Tests for enhanced variable parsing with ${variable:type} syntax.
"""

from typing import Any

import pytest
import typer

from ginx.utils import parse_command_with_extras


class TestVariableParsing:
    """Test the enhanced variable parsing functionality."""

    def test_string_type_basic(self):
        """Test basic string variable parsing."""
        command = "git commit -m ${message:string}"
        result = parse_command_with_extras(command, "fix: bug")
        assert result == 'git commit -m "fix: bug"'

    def test_string_type_with_quotes(self):
        """Test string with internal quotes."""
        command = "echo ${text:string}"
        result = parse_command_with_extras(command, 'He said "hello"')
        assert result == 'echo "He said \\"hello\\""'

    def test_raw_type(self):
        """Test raw variable type (no quoting)."""
        command = "git checkout ${branch:raw}"
        result = parse_command_with_extras(command, "feature/new-parser")
        assert result == "git checkout feature/new-parser"

    def test_number_type_valid(self):
        """Test valid number variable."""
        command = "sleep ${seconds:number}"
        result = parse_command_with_extras(command, "5")
        assert result == "sleep 5"

    def test_number_type_float(self):
        """Test float number variable."""
        command = "sleep ${seconds:number}"
        result = parse_command_with_extras(command, "2.5")
        assert result == "sleep 2.5"

    def test_number_type_invalid(self):
        """Test invalid number raises error."""
        command = "sleep ${seconds:number}"
        with pytest.raises(typer.Exit):
            parse_command_with_extras(command, "abc")

    def test_args_type(self):
        """Test args variable type."""
        command = "git add ${files:args}"
        result = parse_command_with_extras(command, "file1.txt file2.txt")
        # shlex.quote only adds quotes when necessary for shell safety
        assert result == "git add file1.txt file2.txt"

    def test_args_type_with_spaces(self):
        """Test args with filenames containing spaces."""
        command = "git add ${files:args}"
        result = parse_command_with_extras(command, '"my file.txt" other.txt')
        # Only the filename with space gets quoted
        assert result == "git add 'my file.txt' other.txt"

    def test_args_type_needs_quoting(self):
        """Test args that actually need quoting."""
        command = "git add ${files:args}"
        result = parse_command_with_extras(command, "'file with spaces.txt' 'another file.txt'")
        assert result == "git add 'file with spaces.txt' 'another file.txt'"

    def test_multiple_variables_same_value(self):
        """Test multiple variables using same input."""
        command = "git tag -a ${version:string} -m ${version:string}"
        result = parse_command_with_extras(command, "v1.0.0 v1.0.0")
        assert result == 'git tag -a "v1.0.0" -m "v1.0.0"'

    def test_missing_type_required(self):
        """Test that variable type is required."""
        command = "echo ${message}"
        with pytest.raises(typer.Exit):
            parse_command_with_extras(command, "hello")

    def test_invalid_type(self):
        """Test invalid variable type."""
        command = "echo ${message:invalid}"
        with pytest.raises(typer.Exit):
            parse_command_with_extras(command, "hello")

    def test_no_variables_with_input(self, capsys: Any):
        """Test warning when input provided but no variables."""
        command = "echo hello"
        result = parse_command_with_extras(command, "world")
        assert result == "echo hello"

        captured = capsys.readouterr()
        assert "no variable placeholder found" in captured.out

    def test_variables_without_input(self):
        """Test error when variables present but no input."""
        command = "echo ${message:string}"
        with pytest.raises(typer.Exit):
            parse_command_with_extras(command, "")

    def test_empty_input_string(self):
        """Test behavior with empty but non-None input."""
        command = "echo ${message:string}"
        with pytest.raises(typer.Exit):
            parse_command_with_extras(command, "")

    def test_whitespace_handling(self):
        """Test proper whitespace handling."""
        command = "echo ${message:string}"
        result = parse_command_with_extras(command, "  hello world  ")
        assert result == 'echo "hello world"'

    def test_complex_command(self):
        """Test complex command with multiple variable types."""
        command = "docker run --name ${name:raw} -p ${port:number} -v ${volumes:args} ${image:string}"
        # Use input that will produce predictable quoting
        result = parse_command_with_extras(command, 'myapp 8080 "/data:/app /logs:/logs" nginx')
        expected = "docker run --name myapp -p 8080 -v '/data:/app /logs:/logs' \"nginx\""
        assert result == expected
