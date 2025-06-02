"""
Tests for configuration file discovery.
"""

from pathlib import Path
from typing import Any, Dict

from ginx.config.discovery import (
    find_config_file,
    get_project_root,
    list_config_files_in_tree,
)


class TestConfigDiscovery:
    """Test configuration file discovery functionality."""

    def test_find_config_file_in_current_dir(self, config_file: Path, temp_dir: Path):
        """Test finding config file in current directory."""
        result = find_config_file(temp_dir)
        assert result == config_file
        assert result is not None
        assert result.name == "ginx.yaml"

    def test_find_config_file_priority(self, multi_config_dir: Path):
        """Test config file priority order."""
        result = find_config_file(multi_config_dir)
        assert result is not None
        assert result.name == "ginx.yaml"

    def test_find_config_file_in_parent(self, temp_dir: Path, sample_config: Dict[str, Any]):
        """Test finding config file in parent directory."""
        # Create config in temp_dir
        config_path = temp_dir / "ginx.yaml"
        with open(config_path, "w") as f:
            import yaml

            yaml.dump(sample_config, f)

        # Create subdirectory
        sub_dir = temp_dir / "subdir"
        sub_dir.mkdir()

        # Should find config in parent
        result = find_config_file(sub_dir)
        assert result == config_path

    def test_find_config_file_not_found(self, empty_config_dir: Path):
        """Test when no config file exists."""
        result = find_config_file(empty_config_dir)
        assert result is None

    def test_get_project_root(self, config_file: Path, temp_dir: Path):
        """Test getting project root directory."""
        result = get_project_root(temp_dir)
        assert result == temp_dir

    def test_get_project_root_not_found(self, empty_config_dir: Path):
        """Test project root when no config found."""
        result = get_project_root(empty_config_dir)
        assert result is None

    def test_list_config_files_in_tree(self, multi_config_dir: Path):
        """Test listing all config files in tree."""
        results = list_config_files_in_tree(multi_config_dir)
        assert len(results) == 3
        filenames = [r.name for r in results]
        assert "ginx.yaml" in filenames
        assert "ginx.yml" in filenames
        assert ".ginx.yaml" in filenames

    def test_custom_config_names(self, temp_dir: Path):
        """Test finding custom config file names."""
        custom_config = temp_dir / "custom.yaml"
        custom_config.write_text("scripts: {}")

        result = find_config_file(temp_dir, ["custom.yaml"])
        assert result == custom_config
