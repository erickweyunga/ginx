"""
Global settings management.
"""

from typing import Any, Dict, Optional

from .loader import load_config

# Default global settings
DEFAULT_SETTINGS: Dict[str, Any] = {
    "dangerous_commands": True,
}


def load_settings(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load global settings with defaults.

    Args:
        config: Pre-loaded configuration (loads if None)

    Returns:
        Dictionary containing global settings merged with defaults
    """
    if config is None:
        config = load_config()

    settings = config.get("settings", {})

    merged_settings = DEFAULT_SETTINGS.copy()
    merged_settings.update(settings)

    return merged_settings


def get_setting(key: str, default: Any = None, config: Optional[Dict[str, Any]] = None) -> Any:
    """
    Get a specific setting value.

    Args:
        key: Setting key to retrieve
        default: Default value if setting not found
        config: Pre-loaded configuration (loads if None)

    Returns:
        Setting value or default
    """
    settings = load_settings(config)
    return settings.get(key, default)


def is_dangerous_commands_enabled(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Check if dangerous commands are enabled.

    Args:
        config: Pre-loaded configuration (loads if None)

    Returns:
        True if dangerous commands are enabled
    """
    return get_setting("dangerous_commands", True, config)


def get_script_timeout(config: Optional[Dict[str, Any]] = None) -> int:
    """
    Get script execution timeout in seconds.

    Args:
        config: Pre-loaded configuration (loads if None)

    Returns:
        Timeout in seconds
    """
    return get_setting("script_timeout", 300, config)
