"""
Configuration file discovery utilities.
"""

from pathlib import Path
from typing import List, Optional

# Supported configuration file names (in priority order)
DEFAULT_CONFIG_FILES = ["ginx.yaml", "ginx.yml", ".ginx.yaml", ".ginx.yml"]


def find_config_file(
    start_dir: Optional[Path] = None, config_names: Optional[List[str]] = None
) -> Optional[Path]:
    """
    Find the configuration file in the current directory or parent directories.

    Args:
        start_dir: Directory to start searching from (defaults to current directory)
        config_names: List of config file names to search for

    Returns:
        Path to the config file if found, None otherwise.
    """
    if start_dir is None:
        start_dir = Path.cwd()

    if config_names is None:
        config_names = DEFAULT_CONFIG_FILES

    # Check current directory and walk up the tree
    for directory in [start_dir] + list(start_dir.parents):
        for config_name in config_names:
            config_path = directory / config_name
            if config_path.exists():
                return config_path

    return None


def get_project_root(start_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Find the project root by looking for configuration file.

    Args:
        start_dir: Directory to start searching from

    Returns:
        Project root directory if found, None otherwise
    """
    config_file = find_config_file(start_dir)
    return config_file.parent if config_file else None


def list_config_files_in_tree(start_dir: Optional[Path] = None) -> List[Path]:
    """
    Find all configuration files in the directory tree.

    Args:
        start_dir: Directory to start searching from

    Returns:
        List of all config files found
    """
    if start_dir is None:
        start_dir = Path.cwd()

    config_files: List[Path] = []
    for directory in [start_dir] + list(start_dir.parents):
        for config_name in DEFAULT_CONFIG_FILES:
            config_path = directory / config_name
            if config_path.exists():
                config_files.append(config_path)

    return config_files
