"""
Tests for script execution functionality.
"""

from unittest.mock import MagicMock, patch

import pytest
import typer

from ginx.cli.execution import execute_script_logic


class TestScriptExecution:
    """Test script execution functionality."""

    @patch("ginx.cli.execution.get_scripts")
    @patch("ginx.cli.execution.run_command_with_streaming")
    def test_execute_script_success(
        self, mock_run_cmd: MagicMock, mock_get_scripts: MagicMock
    ):
        """Test successful script execution."""
        # Setup mocks
        mock_get_scripts.return_value = {
            "test": {"command": "pytest", "description": "Run tests", "depends": []}
        }
        mock_run_cmd.return_value = 0

        # Execute script - use incremental time values
        with patch("ginx.cli.execution.time.time", side_effect=[0, 1, 2, 3, 4, 5]):
            execute_script_logic("test", {}, "", True, False, False)

        # Verify command was called
        mock_run_cmd.assert_called_once()

    @patch("ginx.cli.execution.get_scripts")
    def test_execute_script_not_found(self, mock_get_scripts: MagicMock):
        """Test executing non-existent script."""
        mock_get_scripts.return_value = {}

        with pytest.raises(typer.Exit):
            execute_script_logic("nonexistent", {}, "", True, False, False)

    @patch("ginx.cli.execution.get_scripts")
    @patch("ginx.cli.execution.validate_command")
    def test_execute_script_validation_fails(
        self, mock_validate: MagicMock, mock_get_scripts: MagicMock
    ):
        """Test script execution with validation failure."""
        mock_get_scripts.return_value = {
            "dangerous": {
                "command": "rm -rf /",
                "description": "Dangerous command",
                "depends": [],
            }
        }
        mock_validate.return_value = False

        with pytest.raises(typer.Exit):
            execute_script_logic("dangerous", {}, "", True, False, False)

    @patch("ginx.cli.execution.get_scripts")
    def test_execute_script_dry_run(
        self, mock_get_scripts: MagicMock, capsys: MagicMock
    ):
        """Test dry run execution."""
        mock_get_scripts.return_value = {
            "test": {"command": "pytest", "description": "Run tests", "depends": []}
        }

        execute_script_logic("test", {}, "", True, True, False)

        captured = capsys.readouterr()
        assert "Dry run - no scripts executed" in captured.out

    @patch("ginx.cli.execution.get_scripts")
    def test_execute_script_with_variables(self, mock_get_scripts: MagicMock):
        """Test executing script with variables."""
        mock_get_scripts.return_value = {
            "commit": {
                "command": "git commit -m ${message:string}",
                "description": "Commit with message",
                "depends": [],
            }
        }

        with patch("ginx.cli.execution.run_command_with_streaming") as mock_run:
            mock_run.return_value = 0
            with patch("ginx.cli.execution.time.time", side_effect=[0, 1, 2, 3, 4, 5]):
                execute_script_logic("commit", {}, "fix: bug", True, False, False)

        # Verify the command was processed with variables
        mock_run.assert_called_once()

    @patch("ginx.cli.execution.get_scripts")
    def test_execute_script_with_dependencies(self, mock_get_scripts: MagicMock):
        """Test executing script with dependencies."""
        mock_get_scripts.return_value = {
            "format": {
                "command": "black .",
                "description": "Format code",
                "depends": [],
            },
            "test": {
                "command": "pytest",
                "description": "Run tests",
                "depends": ["format"],
            },
        }

        with patch("ginx.cli.execution.run_command_with_streaming") as mock_run:
            mock_run.return_value = 0
            # Provide enough time values for dependency execution
            with patch("ginx.cli.execution.time.time", side_effect=list(range(20))):
                execute_script_logic("test", {}, "", True, False, False)

        # Should execute both format and test
        assert mock_run.call_count == 2

    @patch("ginx.cli.execution.get_scripts")
    def test_dependency_validation_failure(self, mock_get_scripts: MagicMock):
        """Test execution fails when dependency validation fails."""
        mock_get_scripts.return_value = {
            "broken": {
                "command": "echo broken",
                "description": "Broken script",
                "depends": ["missing"],  # Missing dependency
            }
        }

        with pytest.raises(typer.Exit):
            execute_script_logic("broken", {}, "", True, False, False)

    @patch("ginx.cli.execution.get_scripts")
    def test_circular_dependency_failure(self, mock_get_scripts: MagicMock):
        """Test execution fails with circular dependencies."""
        mock_get_scripts.return_value = {
            "a": {"command": "echo a", "description": "Script A", "depends": ["b"]},
            "b": {
                "command": "echo b",
                "description": "Script B",
                "depends": ["a"],
            },  # Circular dependency
        }

        with pytest.raises(typer.Exit):
            execute_script_logic("a", {}, "", True, False, False)

    @patch("ginx.cli.execution.get_scripts")
    def test_self_dependency_failure(self, mock_get_scripts: MagicMock):
        """Test execution fails with self-dependency."""
        mock_get_scripts.return_value = {
            "self_dep": {
                "command": "echo self",
                "description": "Self dependent script",
                "depends": ["self_dep"],  # Self dependency
            }
        }

        with pytest.raises(typer.Exit):
            execute_script_logic("self_dep", {}, "", True, False, False)

    @patch("ginx.cli.execution.get_scripts")
    def test_dependency_execution_order(
        self, mock_get_scripts: MagicMock, capsys: MagicMock
    ):
        """Test that dependencies execute in correct order."""
        mock_get_scripts.return_value = {
            "first": {
                "command": "echo first",
                "description": "First script",
                "depends": [],
            },
            "second": {
                "command": "echo second",
                "description": "Second script",
                "depends": ["first"],
            },
        }

        with patch("ginx.cli.execution.run_command_with_streaming") as mock_run:
            mock_run.return_value = 0
            with patch("ginx.cli.execution.time.time", side_effect=list(range(20))):
                execute_script_logic(
                    "second", {}, "", True, False, True
                )  # verbose=True

        captured = capsys.readouterr()
        # Check execution plan is shown
        assert "Execution plan:" in captured.out
        assert "first" in captured.out
        assert "second" in captured.out

        # Should execute both scripts
        assert mock_run.call_count == 2

    @patch("ginx.cli.execution.get_scripts")
    def test_complex_dependency_chain(self, mock_get_scripts: MagicMock):
        """Test complex dependency chain execution."""
        mock_get_scripts.return_value = {
            "format": {
                "command": "black .",
                "description": "Format code",
                "depends": [],
            },
            "lint": {
                "command": "flake8",
                "description": "Lint code",
                "depends": ["format"],
            },
            "test": {
                "command": "pytest",
                "description": "Run tests",
                "depends": ["lint"],
            },
            "build": {
                "command": "python -m build",
                "description": "Build package",
                "depends": ["test"],
            },
        }

        with patch("ginx.cli.execution.run_command_with_streaming") as mock_run:
            mock_run.return_value = 0
            # Provide plenty of time values for complex execution
            with patch("ginx.cli.execution.time.time", side_effect=list(range(50))):
                execute_script_logic("build", {}, "", True, False, False)

        # Should execute all 4 scripts: format, lint, test, build
        assert mock_run.call_count == 4

    @patch("ginx.cli.execution.get_scripts")
    def test_multiple_dependencies(self, mock_get_scripts: MagicMock):
        """Test script with multiple dependencies."""
        mock_get_scripts.return_value = {
            "base1": {
                "command": "echo base1",
                "description": "Base script 1",
                "depends": [],
            },
            "base2": {
                "command": "echo base2",
                "description": "Base script 2",
                "depends": [],
            },
            "target": {
                "command": "echo target",
                "description": "Target script",
                "depends": ["base1", "base2"],  # Multiple dependencies
            },
        }

        with patch("ginx.cli.execution.run_command_with_streaming") as mock_run:
            mock_run.return_value = 0
            with patch("ginx.cli.execution.time.time", side_effect=list(range(30))):
                execute_script_logic("target", {}, "", True, False, False)

        # Should execute all 3 scripts
        assert mock_run.call_count == 3

    @patch("ginx.cli.execution.get_scripts")
    def test_diamond_dependency_pattern(self, mock_get_scripts: MagicMock):
        """Test diamond dependency pattern."""
        mock_get_scripts.return_value = {
            "base": {
                "command": "echo base",
                "description": "Base script",
                "depends": [],
            },
            "left": {
                "command": "echo left",
                "description": "Left branch",
                "depends": ["base"],
            },
            "right": {
                "command": "echo right",
                "description": "Right branch",
                "depends": ["base"],
            },
            "top": {
                "command": "echo top",
                "description": "Top script",
                "depends": ["left", "right"],
            },
        }

        with patch("ginx.cli.execution.run_command_with_streaming") as mock_run:
            mock_run.return_value = 0
            with patch("ginx.cli.execution.time.time", side_effect=list(range(40))):
                execute_script_logic("top", {}, "", True, False, False)

        # Should execute all 4 scripts: base, left, right, top
        assert mock_run.call_count == 4

    @patch("ginx.cli.execution.get_scripts")
    def test_dependency_failure_stops_execution(self, mock_get_scripts: MagicMock):
        """Test that dependency failure stops execution chain."""
        mock_get_scripts.return_value = {
            "failing": {
                "command": "exit 1",  # This will fail
                "description": "Failing script",
                "depends": [],
            },
            "target": {
                "command": "echo target",
                "description": "Target script",
                "depends": ["failing"],
            },
        }

        with patch("ginx.cli.execution.run_command_with_streaming") as mock_run:
            mock_run.return_value = 1  # Simulate failure
            with patch("ginx.cli.execution.time.time", side_effect=list(range(20))):
                with pytest.raises(typer.Exit):
                    execute_script_logic("target", {}, "", True, False, False)

        # Should only execute the failing script, not the target
        assert mock_run.call_count == 1

    @patch("ginx.cli.execution.get_scripts")
    def test_no_dependencies_simple_execution(self, mock_get_scripts: MagicMock):
        """Test simple script execution without dependencies."""
        mock_get_scripts.return_value = {
            "simple": {
                "command": "echo simple",
                "description": "Simple script",
                "depends": [],
            }
        }

        with patch("ginx.cli.execution.run_command_with_streaming") as mock_run:
            mock_run.return_value = 0
            with patch("ginx.cli.execution.time.time", side_effect=list(range(10))):
                execute_script_logic("simple", {}, "", True, False, False)

        # Should execute only one script
        assert mock_run.call_count == 1

    @patch("ginx.cli.execution.get_scripts")
    def test_dependency_with_variables(self, mock_get_scripts: MagicMock):
        """Test dependency execution with variables in target script."""
        mock_get_scripts.return_value = {
            "setup": {
                "command": "echo setup",
                "description": "Setup script",
                "depends": [],
            },
            "deploy": {
                "command": "kubectl apply -f k8s/ --namespace=${env:raw}",
                "description": "Deploy to environment",
                "depends": ["setup"],
            },
        }

        with patch("ginx.cli.execution.run_command_with_streaming") as mock_run:
            mock_run.return_value = 0
            with patch("ginx.cli.execution.time.time", side_effect=list(range(20))):
                execute_script_logic("deploy", {}, "production", True, False, False)

        # Should execute both scripts
        assert mock_run.call_count == 2

    @patch("ginx.cli.execution.get_scripts")
    def test_verbose_dependency_execution(
        self, mock_get_scripts: MagicMock, capsys: MagicMock
    ):
        """Test verbose output during dependency execution."""
        mock_get_scripts.return_value = {
            "format": {
                "command": "black .",
                "description": "Format code",
                "depends": [],
            },
            "test": {
                "command": "pytest",
                "description": "Run tests",
                "depends": ["format"],
            },
        }

        with patch("ginx.cli.execution.run_command_with_streaming") as mock_run:
            mock_run.return_value = 0
            with patch("ginx.cli.execution.time.time", side_effect=list(range(20))):
                execute_script_logic("test", {}, "", True, False, True)  # verbose=True

        captured = capsys.readouterr()

        # Check that execution plan and progress are shown
        assert "Execution plan:" in captured.out
        assert "[1/2] Running: format" in captured.out
        assert "[2/2] Running: test" in captured.out
        assert "All scripts completed successfully" in captured.out

        # Should execute both scripts
        assert mock_run.call_count == 2

    # Alternative approach: Use return_value instead of side_effect for simpler tests
    @patch("ginx.cli.execution.get_scripts")
    def test_simple_execution_alternative_mock(self, mock_get_scripts: MagicMock):
        """Test simple execution using return_value instead of side_effect."""
        mock_get_scripts.return_value = {
            "simple": {
                "command": "echo simple",
                "description": "Simple script",
                "depends": [],
            }
        }

        with patch("ginx.cli.execution.run_command_with_streaming") as mock_run:
            mock_run.return_value = 0
            # Use return_value for simpler mocking - each call returns incrementing time
            with patch("ginx.cli.execution.time.time") as mock_time:
                # Make time.time() return incrementing values
                mock_time.side_effect = lambda: mock_time.call_count
                execute_script_logic("simple", {}, "", True, False, False)

        # Should execute one script
        assert mock_run.call_count == 1
