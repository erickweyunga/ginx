"""
YAML script loader for Ginx CLI tool.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
import yaml
from ginx.init import ginx_config

DEFAULT_CONFIG_FILES = ["ginx.yaml", "ginx.yml", ".ginx.yaml", ".ginx.yml"]

# Default settings
DEFAULT_SETTINGS: dict[str, Any] = {
    "default_shell": "bash",
    "dangerous_commands": True,
    "max_output_lines": 1000,
    "timeout_seconds": 1800,
    "auto_discover_plugins": True,
    "plugin_directories": [],
}


def find_config_file() -> Optional[Path]:
    """
    Find the configuration file in the current directory or parent directories.

    Returns:
        Path to the config file if found, None otherwise.
    """
    current_dir = Path.cwd()

    # Check current directory and walk up the tree
    for directory in [current_dir] + list(current_dir.parents):
        for config_name in DEFAULT_CONFIG_FILES:
            config_path = directory / config_name
            if config_path.exists():
                return config_path

    return None


def load_config() -> Dict[str, Any]:
    """
    Load the complete YAML configuration file.

    Returns:
        Dictionary containing the full configuration with scripts, plugins, and settings.
    """
    config_file = find_config_file()

    if not config_file:
        typer.secho(
            f"No configuration file found. Looking for: {', '.join(DEFAULT_CONFIG_FILES)}",
            fg=typer.colors.YELLOW,
        )
        return {"scripts": {}, "plugins": {}, "settings": DEFAULT_SETTINGS.copy()}

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config: Dict[str, Dict[str, Any]] = yaml.safe_load(f) or {}

        # Ensure all main sections exist
        if "scripts" not in config:
            config["scripts"] = {}
        if "plugins" not in config:
            config["plugins"] = {}
        if "settings" not in config:
            config["settings"] = {}

        # Merge settings with defaults
        merged_settings: dict[str, Any] = DEFAULT_SETTINGS.copy()
        merged_settings.update(config["settings"])
        config["settings"] = merged_settings

        return config

    except yaml.YAMLError as e:
        typer.secho(f"Error parsing YAML file: {e}", fg=typer.colors.RED)
        return {"scripts": {}, "plugins": {}, "settings": DEFAULT_SETTINGS.copy()}
    except FileNotFoundError:
        typer.secho(f"Configuration file not found: {config_file}", fg=typer.colors.RED)
        return {"scripts": {}, "plugins": {}, "settings": DEFAULT_SETTINGS.copy()}
    except Exception as e:
        typer.secho(f"Error loading configuration: {e}", fg=typer.colors.RED)
        return {"scripts": {}, "plugins": {}, "settings": DEFAULT_SETTINGS.copy()}


def load_scripts() -> Dict[str, Dict[str, Any]]:
    """
    Load scripts from the YAML configuration file.

    Returns:
        Dictionary of script configurations.
    """
    config = load_config()
    scripts = config.get("scripts", {})

    if not scripts:
        config_file = find_config_file()
        if config_file:
            typer.secho(
                f"No scripts found in {config_file.name}", fg=typer.colors.YELLOW
            )
        return {}

    # Validate script structure
    validated_scripts: Dict[str, Dict[str, Any]] = {}
    for name, script in scripts.items():
        if isinstance(script, str):
            validated_scripts[name] = {
                "command": script,
                "description": f"Run: {script}",
            }
        elif isinstance(script, dict):
            if "command" not in script:
                typer.secho(
                    f"Script '{name}' missing required 'command' field",
                    fg=typer.colors.RED,
                )
                continue
            validated_scripts[name] = script
        else:
            typer.secho(
                f"Invalid script format for '{name}'. Expected string or dict.",
                fg=typer.colors.RED,
            )
            continue

    return validated_scripts


def load_plugin_config() -> Dict[str, Any]:
    """
    Load plugin configuration from the YAML configuration file.

    Returns:
        Dictionary containing plugin configuration.
    """
    config = load_config()
    plugin_config: Dict[str, Any] = config.get("plugins", {})

    # Validate plugin configuration structure
    validated_config: Dict[str, Any] = {
        "enabled": [],
        "disabled": [],
        "directories": [],
        "settings": {},
    }

    # Handle enabled plugins
    enabled: List[str] = plugin_config.get("enabled", [])
    validated_config["enabled"] = [str(plugin) for plugin in enabled]
    if isinstance(enabled, str):
        validated_config["enabled"] = [enabled]

    # Handle disabled plugins
    disabled: List[str] = plugin_config.get("disabled", [])
    validated_config["disabled"] = [str(plugin) for plugin in disabled]

    # Handle plugin directories
    directories: List[str] = plugin_config.get("directories", [])
    validated_config["directories"] = [str(directory) for directory in directories]
    if isinstance(directories, str):
        validated_config["directories"] = [directories]

    # Handle plugin-specific settings
    settings: Dict[str, Any] = plugin_config.get("settings", {})
    validated_config["settings"] = settings

    return validated_config


def load_global_settings() -> Dict[str, Any]:
    """
    Load global settings from the YAML configuration file.

    Returns:
        Dictionary containing global settings merged with defaults.
    """
    config = load_config()
    return config.get("settings", DEFAULT_SETTINGS.copy())


def get_setting(key: str, default: Any = None) -> Any:
    """
    Get a specific setting value.

    Args:
        key: Setting key to retrieve
        default: Default value if setting not found

    Returns:
        Setting value or default
    """
    settings = load_global_settings()
    return settings.get(key, default)


def is_plugin_enabled(plugin_name: str) -> bool:
    """
    Check if a plugin is enabled in the configuration.

    Args:
        plugin_name: Name of the plugin to check

    Returns:
        True if plugin is enabled, False otherwise
    """
    plugin_config = load_plugin_config()
    enabled_plugins = plugin_config.get("enabled", [])
    disabled_plugins = plugin_config.get("disabled", [])

    # If explicitly disabled, return False
    if plugin_name in disabled_plugins:
        return False

    # If enabled list is empty, auto-enable all plugins (unless disabled)
    if not enabled_plugins:
        return True

    # Check if explicitly enabled
    return plugin_name in enabled_plugins


def get_plugin_directories() -> List[str]:
    """
    Get list of plugin directories from configuration.

    Returns:
        List of directory paths for plugin discovery
    """
    plugin_config = load_plugin_config()
    directories = plugin_config.get("directories", [])

    # Add default directories if auto-discovery is enabled
    settings = load_global_settings()
    if settings.get("auto_discover_plugins", True):
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


def validate_configuration() -> List[str]:
    """
    Validate the entire configuration file and return list of issues.

    Returns:
        List of validation errors/warnings
    """
    issues: List[str] = []
    config = load_config()

    # Validate scripts section
    scripts: Dict[str, Dict[str, Any]] = config.get("scripts", {})
    for script_name, script_config in scripts.items():
        if isinstance(script_config, str):
            continue  # Simple string format is valid

        if "command" not in script_config:
            issues.append(f"Script '{script_name}': Missing required 'command' field")

        # Check working directory if specified
        if "cwd" in script_config:
            cwd_path = Path(script_config["cwd"])
            if not cwd_path.exists():
                issues.append(
                    f"Script '{script_name}': Working directory does not exist: {script_config['cwd']}"
                )

    # Validate plugins section
    plugin_config = config.get("plugins", {})
    if plugin_config and not isinstance(plugin_config, dict):
        issues.append("Plugins section: Expected dictionary format")

    # Validate settings section
    settings: Dict[str, Any] = config.get("settings", {})
    # Validate specific setting types

    if "dangerous_commands" in settings:
        if not isinstance(settings["dangerous_commands"], bool):
            issues.append("Settings: dangerous_commands must be boolean")

    return issues


def create_sample_config(config_path: str = "ginx.yaml") -> None:
    """
    Create a ginx configuration file with all sections.

    Args:
        config_path: Path where to create the ginx config file.
    """

    try:
        clean_config: Dict[str, Any] = {k: v for k, v in ginx_config.items() if not k.startswith("#")}  # type: ignore

        write_ginx_config(clean_config, config_path)

        typer.echo("Edit this file to define your own scripts, plugins, and settings.")

    except Exception as e:
        typer.secho(f"Error creating ginx config: {e}", fg=typer.colors.RED)


def write_ginx_config(config: Dict[str, Any], config_path: str = "ginx.yaml") -> None:
    """
    Write the Ginx configuration file with header and block comments.

    Args:
        config: Dictionary representing the configuration.
        config_path: Output file path.
    """
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            # Header comments
            f.write("# Ginx Configuration File\n")
            f.write("# Define your project scripts and configuration here\n\n")

            # Scripts block
            if "scripts" in config:
                f.write("# Scripts\n")
                yaml.dump(
                    {"scripts": config["scripts"]},
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                    allow_unicode=True,
                )
                f.write("\n")

            # Plugins block
            if "plugins" in config:
                f.write("# Plugins\n")
                yaml.dump(
                    {"plugins": config["plugins"]},
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                    allow_unicode=True,
                )
                f.write("\n")

            # Settings block
            if "settings" in config:
                f.write("# Settings\n")
                yaml.dump(
                    {"settings": config["settings"]},
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                    allow_unicode=True,
                )
                f.write("\n")

        typer.secho(f"Ginx config written to {config_path}", fg=typer.colors.GREEN)

    except Exception as e:
        typer.secho(f"Failed to write config: {e}", fg=typer.colors.RED)
        raise e


def get_scripts() -> Dict[str, Dict[str, Any]]:
    """Alias for load_scripts()"""
    return load_scripts()


def get_plugin_config() -> Dict[str, Any]:
    """Alias for load_plugin_config()"""
    return load_plugin_config()


def get_global_config() -> Dict[str, Any]:
    """Alias for load_global_settings()"""
    return load_global_settings()
