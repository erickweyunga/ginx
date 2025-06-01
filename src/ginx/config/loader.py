"""
Core YAML configuration loading.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml
import typer

from .discovery import find_config_file


class Configconfigror(Exception):
    """Exception raised when configuration loading fails."""

    pass


def load_raw_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load raw YAML configuration from file.

    Args:
        config_path: Path to config file (auto-discovered if None)

    Returns:
        Raw configuration dictionary

    Raises:
        Configconfigror: If configuration cannot be loaded
    """
    if config_path is None:
        config_path = find_config_file()

    if not config_path:
        raise Configconfigror("No configuration file found")

    if not config_path.exists():
        raise Configconfigror(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config: Dict[Any, Any] = yaml.safe_load(f) or {}

        return config

    except yaml.YAMLError as e:
        raise Configconfigror(f"Error parsing YAML file: {e}")
    except Exception as e:
        raise Configconfigror(f"Error loading configuration: {e}")


def normalize_config(raw_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize configuration structure with default sections.

    Args:
        raw_config: Raw configuration dictionary

    Returns:
        Normalized configuration with all expected sections
    """
    normalized: Dict[str, Dict[str, Any]] = {
        "scripts": {},
        "plugins": {},
        "settings": {},
    }

    # Merge with provided config
    for section in normalized:
        if section in raw_config:
            normalized[section] = raw_config[section]

    return normalized


def load_config(
    config_path: Optional[Path] = None, silent: bool = False
) -> Dict[str, Any]:
    """
    Load and normalize configuration with error handling.

    Args:
        config_path: Path to config file (auto-discovered if None)
        silent: Whether to suppress error messages

    Returns:
        Normalized configuration dictionary (empty sections if load fails)
    """
    try:
        raw_config = load_raw_config(config_path)
        return normalize_config(raw_config)

    except Configconfigror as e:
        if not silent:
            if "No configuration file found" in str(e):
                from .discovery import DEFAULT_CONFIG_FILES

                typer.secho(
                    f"No configuration file found. Looking for: {', '.join(DEFAULT_CONFIG_FILES)}",
                    fg=typer.colors.YELLOW,
                )
            else:
                typer.secho(str(e), fg=typer.colors.RED)

        # Return empty config structure
        return normalize_config({})


def save_config(config: Dict[str, Any], config_path: str = "ginx.yaml") -> None:
    """
    Save configuration to YAML file with proper formatting.

    Args:
        config: Configuration dictionary to save
        config_path: Output file path
    """
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            # Header comments
            f.write("# Ginx Configuration File\n")
            f.write("# Define your project scripts and configuration here\n\n")

            # Write each section with comments
            for section_name in ["scripts", "plugins", "settings"]:
                if section_name in config and config[section_name]:
                    f.write(f"# {section_name.title()}\n")
                    yaml.dump(
                        {section_name: config[section_name]},
                        f,
                        default_flow_style=False,
                        sort_keys=False,
                        indent=2,
                        allow_unicode=True,
                    )
                    f.write("\n")

        typer.secho(f"Configuration saved to {config_path}", fg=typer.colors.GREEN)

    except Exception as e:
        typer.secho(f"Failed to save config: {e}", fg=typer.colors.RED)
        raise
