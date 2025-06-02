"""
Plugin configuration management.
"""

from typing import Any, Dict, List, Optional, Union

from .loader import load_config
from .settings import get_setting


def load_plugin_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load and validate plugin configuration.

    Args:
        config: Pre-loaded configuration (loads if None)

    Returns:
        Dictionary containing validated plugin configuration
    """
    if config is None:
        config = load_config()

    plugin_config = config.get("plugins", {})

    validated_config: Dict[str, Any] = {
        "enabled": _normalize_plugin_list(plugin_config.get("enabled", [])),
        "disabled": _normalize_plugin_list(plugin_config.get("disabled", [])),
        "directories": _normalize_plugin_list(plugin_config.get("directories", [])),
        "settings": plugin_config.get("settings", {}),
    }

    return validated_config


def _normalize_plugin_list(value: Union[str, List[Optional[str]]]) -> List[str]:
    """
    Normalize plugin list configuration.

    Args:
        value: Plugin list value (string or list)

    Returns:
        Normalized list of strings
    """
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if item is not None]


def is_plugin_enabled(plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Check if a plugin is enabled.

    Args:
        plugin_name: Name of the plugin to check
        config: Pre-loaded configuration (loads if None)

    Returns:
        True if plugin is enabled, False otherwise
    """
    plugin_config = load_plugin_config(config)
    enabled_plugins = plugin_config["enabled"]
    disabled_plugins = plugin_config["disabled"]

    # If explicitly disabled, return False
    if plugin_name in disabled_plugins:
        return False

    # If enabled list is empty, auto-enable all plugins (unless disabled)
    if not enabled_plugins:
        return True

    return plugin_name in enabled_plugins


def get_plugin_directories(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Get list of plugin directories.

    Args:
        config: Pre-loaded configuration (loads if None)

    Returns:
        List of directory paths for plugin discovery
    """
    plugin_config = load_plugin_config(config)
    directories = plugin_config["directories"]

    # Add default directories if auto-discovery is enabled
    if get_setting("auto_discover_plugins", True, config):
        default_dirs = [
            "ginx_plugins",
            "~/.ginx/plugins",
            "/usr/local/share/ginx/plugins",
        ]

        # Add defaults if not already specified
        for default_dir in default_dirs:
            if default_dir not in directories:
                directories.append(default_dir)

    return directories


def get_plugin_settings(plugin_name: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get settings for a specific plugin.

    Args:
        plugin_name: Name of the plugin
        config: Pre-loaded configuration (loads if None)

    Returns:
        Plugin-specific settings dictionary
    """
    plugin_config = load_plugin_config(config)
    all_plugin_settings = plugin_config["settings"]

    return all_plugin_settings.get(plugin_name, {})
