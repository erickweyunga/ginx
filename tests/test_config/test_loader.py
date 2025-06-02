"""
Tests for configuration loading functionality.
"""

from pathlib import Path
from typing import Any, Dict

import pytest

from ginx.config.loader import (
    ConfigLoadError,
    load_config,
    load_raw_config,
    normalize_config,
    save_config,
)


class TestConfigLoader:
    """Test configuration loading functionality."""

    def test_load_raw_config_success(self, config_file: Path):
        """Test successful raw config loading."""
        config = load_raw_config(config_file)
        assert isinstance(config, dict)
        assert "scripts" in config
        assert "plugins" in config
        assert "settings" in config

    def test_load_raw_config_not_found(self, temp_dir: Path):
        """Test loading non-existent config file."""
        non_existent = temp_dir / "missing.yaml"
        with pytest.raises(ConfigLoadError):
            load_raw_config(non_existent)

    def test_load_raw_config_invalid_yaml(self, temp_dir: Path):
        """Test loading invalid YAML."""
        invalid_yaml = temp_dir / "invalid.yaml"
        invalid_yaml.write_text("invalid: yaml: content:")

        with pytest.raises(ConfigLoadError):
            load_raw_config(invalid_yaml)

    def test_normalize_config(self):
        """Test config normalization."""
        raw_config = {"scripts": {"test": "pytest"}}
        normalized = normalize_config(raw_config)

        assert "scripts" in normalized
        assert "plugins" in normalized
        assert "settings" in normalized
        assert normalized["scripts"]["test"] == "pytest"

    def test_load_config_success(self, config_file: Path):
        """Test successful config loading."""
        config = load_config(config_file)
        assert isinstance(config, dict)
        assert all(section in config for section in ["scripts", "plugins", "settings"])

    def test_load_config_missing_file_silent(self, temp_dir: Path):
        """Test loading missing file silently."""
        config = load_config(temp_dir / "missing.yaml", silent=True)
        assert config == {"scripts": {}, "plugins": {}, "settings": {}}

    def test_save_config(self, temp_dir: Path):
        """Test saving configuration."""
        config: Dict[str, Any] = {
            "scripts": {"test": {"command": "pytest"}},
            "plugins": {"enabled": []},
            "settings": {"dangerous_commands": True},
        }

        output_path = temp_dir / "output.yaml"
        save_config(config, str(output_path))

        assert output_path.exists()

        # Verify saved content
        with open(output_path) as f:
            content = f.read()
            assert "# Ginx Configuration File" in content
            assert "scripts:" in content
            assert "plugins:" in content
            assert "settings:" in content
