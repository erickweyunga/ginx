"""
Version synchronization and update checking plugin for Ginx.

This plugin adds commands for checking package updates, syncing versions with PyPI,
and managing dependency versions across different environments.
"""

from .core import VersionSyncPlugin

__all__ = ["VersionSyncPlugin"]
