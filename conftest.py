"""
Pytest configuration and shared fixtures.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    config: Dict[str, Any] = {
        "scripts": {
            "test": {"command": "pytest", "description": "Run tests"},
            "commit": {
                "command": "git commit -m ${message:string}",
                "description": "Commit with message",
                "depends": [],
            },
            "checkout": {
                "command": "git checkout ${branch:raw}",
                "description": "Switch branch",
                "depends": [],
            },
            "sleep": {
                "command": "sleep ${seconds:number}",
                "description": "Sleep for seconds",
                "depends": [],
            },
            "add": {"command": "git add ${files:args}", "description": "Add files"},
            "version": {  # Reserved command conflict
                "command": "echo v1.0.0",
                "description": "Show version",
                "depends": [],
            },
            "lint": {
                "command": "flake8",
                "description": "Lint code",
                "depends": ["format"],
            },
            "full-test": {
                "command": "pytest --cov",
                "description": "Full test with coverage",
                "depends": ["lint", "test"],
            },
        },
        "plugins": {
            "enabled": ["version-sync"],
        },
        "settings": {
            "dangerous_commands": True,
        },
    }
    return config


@pytest.fixture
def config_file(temp_dir: Path, sample_config: Dict[str, Any]) -> Path:
    """Create a temporary config file."""
    config_path = temp_dir / "ginx.yaml"
    with open(config_path, "w") as f:
        yaml.dump(sample_config, f)
    return config_path


@pytest.fixture
def empty_config_dir(temp_dir: Path) -> Path:
    """Directory with no config file."""
    return temp_dir


@pytest.fixture
def multi_config_dir(temp_dir: Path) -> Path:
    """Directory with multiple config files."""
    configs = {
        "ginx.yaml": {"scripts": {"test1": "echo test1"}},
        "ginx.yml": {"scripts": {"test2": "echo test2"}},
        ".ginx.yaml": {"scripts": {"test3": "echo test3"}},
    }

    for filename, config in configs.items():
        config_path = temp_dir / filename
        with open(config_path, "w") as f:
            yaml.dump(config, f)

    return temp_dir
