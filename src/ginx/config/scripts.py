"""
Script configuration loading and validation.
"""

from typing import Any, Dict, Optional, Set, cast
import typer

from ginx.cmd import RESERVED_COMMANDS

from .loader import load_config


def is_script_name_reserved(script_name: str) -> bool:
    """
    Check if a script name conflicts with reserved commands.

    Args:
        script_name: Name of the script to check

    Returns:
        True if script name is reserved, False otherwise
    """
    return script_name in RESERVED_COMMANDS


def load_scripts(
    config: Optional[Dict[str, Any]] = None, show_warnings: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    Load and validate script configurations, excluding reserved names.

    Args:
        config: Pre-loaded configuration (loads if None)
        show_warnings: Whether to show warnings for skipped scripts

    Returns:
        Dictionary of validated script configurations
    """
    if config is None:
        config = load_config()

    scripts = config.get("scripts", {})

    if not scripts:
        return {}

    validated_scripts: Dict[str, Dict[str, Any]] = {}

    for name, script in scripts.items():
        if is_script_name_reserved(name):
            if show_warnings:
                typer.secho(
                    f"Warning: Script '{name}' conflicts with built-in command. Skipping.",
                    fg=typer.colors.YELLOW,
                )
            continue

        validated_script = validate_script_config(name, script)
        if validated_script:
            validated_scripts[name] = validated_script

    return validated_scripts


def validate_script_config(name: str, script: Any) -> Optional[Dict[str, Any]]:
    """
    Validate and normalize a single script configuration.

    Args:
        name: Script name
        script: Script configuration (string or dict)

    Returns:
        Validated script configuration or None if invalid
    """
    if isinstance(script, str):
        return {
            "command": script,
            "description": f"Run: {script}",
        }

    elif isinstance(script, dict):
        if "command" not in script:
            typer.secho(
                f"Script '{name}' missing required 'command' field",
                fg=typer.colors.RED,
            )
            return None

        if "description" not in script:
            script["description"] = f"Run {name} script"

        typed_script: Dict[str, Any] = cast(Dict[str, Any], script)
        return typed_script

    else:
        typer.secho(
            f"Invalid script format for '{name}'. Expected string or dict.",
            fg=typer.colors.RED,
        )
        return None


def get_script_variables(script_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract variable definitions from script configuration.

    Args:
        script_config: Script configuration dictionary

    Returns:
        Dictionary of variable definitions
    """
    return script_config.get("variables", {})


def has_variables(script_config: Dict[str, Any]) -> bool:
    """
    Check if script has variable definitions.

    Args:
        script_config: Script configuration dictionary

    Returns:
        True if script has variables defined
    """
    command = script_config.get("command", "")
    variables = script_config.get("variables", {})

    # Check for variable syntax in command
    has_new_syntax = "${" in command
    has_legacy_syntax = "EXTRA_" in command
    has_variable_definitions = bool(variables)

    return has_new_syntax or has_legacy_syntax or has_variable_definitions


def get_reserved_commands() -> Set[str]:
    """
    Get the set of reserved command names.

    Returns:
        Set of reserved command names
    """
    return RESERVED_COMMANDS.copy()


def add_reserved_command(command_name: str) -> None:
    """
    Add a command name to the reserved list (for plugins).

    Args:
        command_name: Command name to reserve
    """
    RESERVED_COMMANDS.add(command_name)


def list_conflicting_scripts(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get list of scripts that conflict with reserved commands.

    Args:
        config: Pre-loaded configuration (loads if None)

    Returns:
        Dictionary of conflicting script names and their configs
    """
    if config is None:
        config = load_config()

    scripts = config.get("scripts", {})
    conflicts: Dict[str, Any] = {}

    for name, script in scripts.items():
        if is_script_name_reserved(name):
            conflicts[name] = script

    return conflicts
