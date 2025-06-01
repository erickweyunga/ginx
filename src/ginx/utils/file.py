"""
File and project-related utility functions.
"""

import os
from pathlib import Path
from typing import List, Optional

import typer

from ginx.constants import COMMON_PROJECT_ROOT_MARKERS, DEFAULT_REQUIREMENTS_FILES


def get_project_root() -> Optional[Path]:
    """
    Find the project root directory by looking for common markers.

    Returns:
        Path to project root if found, None otherwise
    """
    current = Path.cwd()

    for directory in [current] + list(current.parents):
        for marker in COMMON_PROJECT_ROOT_MARKERS:
            if (directory / marker).exists():
                return directory

    return None


def safe_filename(filename: str) -> str:
    """
    Convert a string to a safe filename by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Safe filename
    """
    # Characters not allowed in filenames
    invalid_chars = '<>:"/\\|?*'

    safe_name = filename
    for char in invalid_chars:
        safe_name = safe_name.replace(char, "_")

    # Remove leading/trailing whitespace and dots
    safe_name = safe_name.strip(" .")

    # Ensure it's not empty
    if not safe_name:
        safe_name = "unnamed"

    return safe_name


def find_requirements_files() -> List[str]:
    """Find available requirements files in the project."""
    found_files: List[str] = []
    for req_file in DEFAULT_REQUIREMENTS_FILES:
        if os.path.exists(req_file):
            found_files.append(req_file)
    return found_files


def parse_requirements_file(file_path: str) -> List[str]:
    """Parse a requirements file and return list of packages."""
    packages: List[str] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith("#") and not line.startswith("-"):
                    # Handle package names with version specifiers
                    package_name = (
                        line.split("==")[0]
                        .split(">=")[0]
                        .split("<=")[0]
                        .split("~=")[0]
                        .split(">")[0]
                        .split("<")[0]
                        .strip()
                    )
                    if package_name:
                        packages.append(
                            line
                        )  # Keep full specification for installation
    except Exception as e:
        typer.secho(
            f"Warning: Could not parse {file_path}: {e}", fg=typer.colors.YELLOW
        )
    return packages
