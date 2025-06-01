"""
PyPI API interaction utilities.
"""

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class PyPIClient:
    """Client for interacting with PyPI API."""

    def __init__(self, user_agent: str = "ginx-version-sync-plugin/1.0.0"):
        self.user_agent = user_agent
        self.base_url = "https://pypi.org/pypi"

    def get_package_info(
        self, package_name: str, timeout: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Get package information from PyPI API.

        Args:
            package_name: Name of the package
            timeout: Request timeout in seconds

        Returns:
            Package information dict or None if failed
        """
        try:
            url = f"{self.base_url}/{package_name}/json"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", self.user_agent)

            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            json.JSONDecodeError,
            TimeoutError,
        ):
            return None

    def get_latest_version(self, package_name: str, timeout: int = 10) -> Optional[str]:
        """
        Get the latest version of a package from PyPI.

        Args:
            package_name: Name of the package
            timeout: Request timeout in seconds

        Returns:
            Latest version string or None if failed
        """
        package_info = self.get_package_info(package_name, timeout)
        if package_info:
            return str(package_info.get("info", {}).get("version"))
        return None

    def get_package_releases(
        self, package_name: str, timeout: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Get all releases for a package from PyPI.

        Args:
            package_name: Name of the package
            timeout: Request timeout in seconds

        Returns:
            Releases information dict or None if failed
        """
        package_info: Optional[Dict[str, Any]] = self.get_package_info(package_name, timeout)
        if package_info:
            return package_info.get("releases", {})
        return None

    def package_exists(self, package_name: str, timeout: int = 10) -> bool:
        """
        Check if a package exists on PyPI.

        Args:
            package_name: Name of the package
            timeout: Request timeout in seconds

        Returns:
            True if package exists, False otherwise
        """
        return self.get_package_info(package_name, timeout) is not None

    def get_package_summary(
        self, package_name: str, timeout: int = 10
    ) -> Optional[str]:
        """
        Get package summary/description from PyPI.

        Args:
            package_name: Name of the package
            timeout: Request timeout in seconds

        Returns:
            Package summary or None if failed
        """
        package_info = self.get_package_info(package_name, timeout)
        if package_info:
            return str(package_info.get("info", {}).get("summary"))
        return None


# Global client instance
_pypi_client = PyPIClient()


def get_pypi_package_info(
    package_name: str, timeout: int = 10
) -> Optional[Dict[str, Any]]:
    """Get package information from PyPI API (convenience function)."""
    return _pypi_client.get_package_info(package_name, timeout)


def get_latest_version(package_name: str, timeout: int = 10) -> Optional[str]:
    """Get the latest version of a package from PyPI (convenience function)."""
    return _pypi_client.get_latest_version(package_name, timeout)


def package_exists(package_name: str, timeout: int = 10) -> bool:
    """Check if a package exists on PyPI (convenience function)."""
    return _pypi_client.package_exists(package_name, timeout)
