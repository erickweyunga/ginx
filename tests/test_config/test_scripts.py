"""
Tests for script configuration loading and validation.
"""

from typing import Any, Dict

from ginx.config.scripts import (
    get_reserved_commands,
    is_script_name_reserved,
    list_conflicting_scripts,
    load_scripts,
    validate_script_config,
)


class TestScriptConfiguration:
    """Test script configuration functionality."""

    def test_load_scripts_success(self, sample_config: Dict[str, Any]):
        """Test successful script loading."""
        scripts = load_scripts(sample_config)

        # Should exclude reserved 'version' command
        assert "test" in scripts
        assert "commit" in scripts
        assert "version" not in scripts  # Reserved command excluded

    def test_load_scripts_empty_config(self):
        """Test loading with empty config."""
        config: Dict[str, Any] = {"scripts": {}}
        scripts = load_scripts(config)
        assert scripts == {}

    def test_validate_script_config_string(self):
        """Test validating string script config."""
        result = validate_script_config("test", "pytest")
        expected: Dict[str, Any] = {
            "command": "pytest",
            "description": "Run: pytest",
            "depends": [],
        }
        assert result == expected

    def test_validate_script_config_dict(self):
        """Test validating dictionary script config."""
        script = {"command": "pytest", "description": "Run tests"}
        result = validate_script_config("test", script)
        assert result == script

    def test_validate_script_config_single_dependency_string(self):
        """Test converting single dependency string to list."""
        script = {"command": "pytest", "description": "Run tests", "depends": "format"}
        result = validate_script_config("test", script)
        expected: Dict[str, Any] = {
            "command": "pytest",
            "description": "Run tests",
            "depends": ["format"],
        }
        assert result == expected

    def test_validate_script_config_dict_no_description(self):
        """Test dict config without description gets default."""
        script = {"command": "pytest"}
        result = validate_script_config("test", script)
        assert result is not None
        assert result["description"] == "Run test script"
        assert result["depends"] == []

    def test_validate_script_config_missing_command(self, capsys: Any):
        """Test validation fails for missing command."""
        script = {"description": "Test script"}
        result = validate_script_config("test", script)
        assert result is None

        captured = capsys.readouterr()
        assert "missing required 'command' field" in captured.out

    def test_validate_script_config_invalid_type(self, capsys: Any):
        """Test validation fails for invalid type."""
        result = validate_script_config("test", 123)
        assert result is None

        captured = capsys.readouterr()
        assert "Invalid script format" in captured.out

    def test_is_script_name_reserved(self):
        """Test reserved command checking."""
        assert is_script_name_reserved("version") is True
        assert is_script_name_reserved("list") is True
        assert is_script_name_reserved("test") is False
        assert is_script_name_reserved("my-script") is False

    def test_get_reserved_commands(self):
        """Test getting reserved commands."""
        reserved = get_reserved_commands()
        assert isinstance(reserved, set)
        assert "version" in reserved
        assert "list" in reserved
        assert len(reserved) > 0

    def test_list_conflicting_scripts(self, sample_config: Dict[str, Any]):
        """Test finding conflicting scripts."""
        conflicts = list_conflicting_scripts(sample_config)
        assert "version" in conflicts
        assert conflicts["version"]["command"] == "echo v1.0.0"

    def test_load_scripts_shows_warnings(self, sample_config: Dict[str, Any], capsys: Any):
        """Test that warnings are shown for conflicting scripts."""
        load_scripts(sample_config, show_warnings=True)
        captured = capsys.readouterr()
        assert "conflicts with built-in command" in captured.out

    def test_load_scripts_no_warnings(self, sample_config: Dict[str, Any], capsys: Any):
        """Test suppressing warnings."""
        load_scripts(sample_config, show_warnings=False)
        captured = capsys.readouterr()
        assert "conflicts with built-in command" not in captured.out
