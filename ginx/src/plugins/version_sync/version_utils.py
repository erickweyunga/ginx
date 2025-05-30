"""
Version parsing and comparison utilities.
"""

from typing import Tuple

try:
    from packaging.version import InvalidVersion, parse

    has_packaging = True
except ImportError:
    parse = None
    InvalidVersion = Exception
    has_packaging = False


def has_packaging_library() -> bool:
    """Check if the packaging library is available."""
    return has_packaging


def parse_package_line(line: str) -> Tuple[str, str, str]:
    """
    Parse a package line and return (name, operator, version).

    Args:
        line: Package requirement line (e.g., "requests>=2.0.0")

    Returns:
        Tuple of (package_name, operator, version_spec)
    """
    line = line.strip()

    # Skip comments and empty lines
    if not line or line.startswith("#") or line.startswith("-"):
        return "", "", ""

    # Handle different version specifiers
    for op in [">=", "<=", "==", "~=", "!=", ">", "<"]:
        if op in line:
            parts = line.split(op, 1)
            if len(parts) == 2:
                package_name = parts[0].strip()
                version_spec = parts[1].strip()
                return package_name, op, version_spec

    # No version specifier found
    return line, "", ""


def compare_versions(current: str, latest: str) -> str:
    """
    Compare versions and return status.

    Args:
        current: Current version string
        latest: Latest version string

    Returns:
        Status: "current", "outdated", "ahead", or "unknown"
    """
    if not has_packaging:
        # Fallback to string comparison if packaging is not available
        if current == latest:
            return "current"
        else:
            return "unknown"
    if parse is None:
        return "unknown"
    try:
        current_ver = parse(current)
        latest_ver = parse(latest)

        if current_ver < latest_ver:
            return "outdated"
        elif current_ver > latest_ver:
            return "ahead"
        else:
            return "current"
    except InvalidVersion:
        return "unknown"


def normalize_package_name(name: str) -> str:
    """
    Normalize package name for consistent comparison.

    Args:
        name: Package name

    Returns:
        Normalized package name
    """
    return name.lower().replace("_", "-")


def format_version_comparison(
    package: str, current: str, latest: str, status: str
) -> str:
    """
    Format version comparison for display.

    Args:
        package: Package name
        current: Current version
        latest: Latest version
        status: Comparison status

    Returns:
        Formatted string for display
    """
    if status == "outdated":
        return f"{package}: {current} → {latest}"
    elif status == "ahead":
        return f"{package}: {current} (ahead of PyPI: {latest})"
    elif status == "current":
        return f"{package}: {current} (up to date)"
    else:
        return f"{package}: {current} (status: {status})"
