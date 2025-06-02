"""
Tests for script dependency functionality.
"""

from typing import Any, Dict

from ginx.config.scripts import (
    detect_dependency_cycles,
    resolve_execution_order,
    validate_dependencies,
)


class TestScriptDependencies:
    """Test script dependency functionality."""

    def test_simple_dependency_chain(self):
        """Test simple dependency chain: A → B → C."""
        scripts: Dict[str, Any] = {
            "c": {"command": "echo c", "depends": []},
            "b": {"command": "echo b", "depends": ["c"]},
            "a": {"command": "echo a", "depends": ["b"]},
        }

        order = resolve_execution_order(scripts, "a")
        assert order == ["c", "b", "a"]

    def test_multiple_dependencies(self):
        """Test script with multiple dependencies."""
        scripts: Dict[str, Any] = {
            "base1": {"command": "echo base1", "depends": []},
            "base2": {"command": "echo base2", "depends": []},
            "target": {"command": "echo target", "depends": ["base1", "base2"]},
        }

        order = resolve_execution_order(scripts, "target")
        # base1 and base2 can be in any order, but both before target
        assert len(order) == 3
        assert order[-1] == "target"  # target should be last
        assert "base1" in order
        assert "base2" in order

    def test_diamond_dependency(self):
        """Test diamond dependency pattern."""
        scripts: Dict[str, Any] = {
            "base": {"command": "echo base", "depends": []},
            "left": {"command": "echo left", "depends": ["base"]},
            "right": {"command": "echo right", "depends": ["base"]},
            "top": {"command": "echo top", "depends": ["left", "right"]},
        }

        order = resolve_execution_order(scripts, "top")
        assert order[0] == "base"  # base must be first
        assert order[-1] == "top"  # top must be last
        assert "left" in order
        assert "right" in order

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        scripts: Dict[str, Any] = {
            "a": {"command": "echo a", "depends": ["b"]},
            "b": {"command": "echo b", "depends": ["c"]},
            "c": {"command": "echo c", "depends": ["a"]},  # Creates cycle
        }

        cycles = detect_dependency_cycles(scripts)
        assert len(cycles) > 0
        # Should detect the cycle a → b → c → a

    def test_self_dependency_detection(self):
        """Test detection of self-dependencies."""
        scripts: Dict[str, Any] = {
            "self_dep": {"command": "echo self", "depends": ["self_dep"]},
        }

        errors = validate_dependencies(scripts)
        assert any("cannot depend on itself" in error for error in errors)

    def test_missing_dependency_detection(self):
        """Test detection of missing dependencies."""
        scripts: Dict[str, Any] = {
            "existing": {"command": "echo existing", "depends": ["missing"]},
        }

        errors = validate_dependencies(scripts)
        assert any("non-existent script" in error for error in errors)

    def test_no_dependencies(self):
        """Test script with no dependencies."""
        scripts: Dict[str, Any] = {
            "simple": {"command": "echo simple", "depends": []},
        }

        order = resolve_execution_order(scripts, "simple")
        assert order == ["simple"]

    def test_complex_dependency_graph(self):
        """Test complex dependency resolution."""
        scripts: Dict[str, Any] = {
            "format": {"command": "black .", "depends": []},
            "lint": {"command": "flake8", "depends": ["format"]},
            "test": {"command": "pytest", "depends": ["lint"]},
            "build": {"command": "python -m build", "depends": ["test"]},
            "publish": {"command": "twine upload", "depends": ["build"]},
        }

        order = resolve_execution_order(scripts, "publish")
        expected = ["format", "lint", "test", "build", "publish"]
        assert order == expected
