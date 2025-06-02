"""
Core built-in commands: version, list, validate, deps.
"""

import typing
from typing import List, Optional

import typer

from ginx.config import get_scripts, resolve_execution_order
from ginx.constants import COMMON_SHELL_RESERVED_COMMANDS
from ginx.utils import (
    check_dependencies,
    extract_commands_from_shell_string,
    find_requirements_files,
    parse_requirements_file,
    validate_command,
)


def version_command() -> None:
    """Show the current version of Ginx."""
    try:
        from ginx import __version__

        typer.echo(f"Ginx version {__version__}")
    except ImportError:
        typer.echo("Version information not available")


def list_scripts_command() -> None:
    """Display all scripts from the YAML configuration."""
    scripts = get_scripts()
    if not scripts:
        typer.echo("No scripts found.")
        raise typer.Exit()

    typer.secho("Available scripts:", fg=typer.colors.BLUE, bold=True)
    typer.echo()

    for name, data in scripts.items():
        description = data.get("description", "No description")
        command = data.get("command", "")

        typer.secho(f"  {name}", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"    Description: {description}")
        typer.echo(f"    Command: {command}")
        typer.echo()


def validate_config_command() -> None:
    """Validate the YAML configuration file and check for issues."""
    scripts = get_scripts()

    if not scripts:
        typer.secho("No valid configuration found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho("Configuration validation:", fg=typer.colors.BLUE, bold=True)
    typer.echo()

    issues_found = False

    for name, script in scripts.items():
        typer.secho(f"Script: {name}", fg=typer.colors.GREEN)

        # Check required fields
        if "command" not in script:
            typer.secho(f"  ✗ Missing required 'command' field", fg=typer.colors.RED)
            issues_found = True
        else:
            typer.secho(f"  ✓ Command: {script['command']}", fg=typer.colors.GREEN)

        # Check command validity
        if "command" in script and not validate_command(script["command"]):
            typer.secho(f"  ⚠ Command validation warning", fg=typer.colors.YELLOW)

        # Check working directory
        if "cwd" in script:
            import os

            if not os.path.exists(script["cwd"]):
                typer.secho(
                    f"  ⚠ Working directory does not exist: {script['cwd']}",
                    fg=typer.colors.YELLOW,
                )

        typer.echo()

    if issues_found:
        typer.secho(
            "Configuration has issues that need to be fixed.", fg=typer.colors.RED
        )
        raise typer.Exit(code=1)
    else:
        typer.secho("✓ Configuration is valid!", fg=typer.colors.GREEN, bold=True)


def check_dependencies_command() -> None:
    """Check if required commands/tools are available and show requirements file status."""
    scripts = get_scripts()

    # Check requirements files
    req_files = find_requirements_files()
    if req_files:
        typer.secho("Found requirements files:", fg=typer.colors.BLUE, bold=True)
        for req_file in req_files:
            packages = parse_requirements_file(req_file)
            typer.echo(f"  {req_file}: {len(packages)} packages")
        typer.echo()

    if not scripts:
        typer.secho("No scripts found.", fg=typer.colors.RED)
        if not req_files:
            raise typer.Exit(code=1)
        return

    # Extract commands from scripts
    commands_to_check: typing.Set[str] = set()
    for script in scripts.values():
        command = script.get("command", "")
        if command:
            found_commands = extract_commands_from_shell_string(command)
            all_commands: List[str] = []
            for command in found_commands:
                if command not in COMMON_SHELL_RESERVED_COMMANDS:
                    all_commands.append(command)
            commands_to_check.update(all_commands)

    if not commands_to_check:
        typer.echo("No external commands found in scripts.")
        return

    typer.secho("Script dependencies:", fg=typer.colors.BLUE, bold=True)

    results = check_dependencies(list(commands_to_check))
    missing_commands: List[str] = []

    for cmd, available in results.items():
        if available:
            typer.secho(f"  ✓ {cmd}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"  ✗ {cmd}", fg=typer.colors.RED)
            missing_commands.append(cmd)

    if missing_commands:
        typer.echo()
        typer.secho("Missing commands:", fg=typer.colors.RED, bold=True)
        for cmd in missing_commands:
            typer.echo(f"  - {cmd}")

        typer.echo()
        typer.secho("Install missing dependencies")
        typer.secho(f"Use command: pip install {' '.join(missing_commands)}")
        typer.echo()


def show_dependency_graph(
    script_name: Optional[str] = typer.Argument(None, help="Script to analyze")
) -> None:
    """Show dependency graph for all scripts or a specific script."""
    scripts = get_scripts()

    if script_name:
        if script_name not in scripts:
            typer.secho(f"Script '{script_name}' not found.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        execution_order = resolve_execution_order(scripts, script_name)
        typer.secho(
            f"Dependency chain for '{script_name}':", fg=typer.colors.BLUE, bold=True
        )
        for i, script in enumerate(execution_order):
            typer.echo(f"  {i+1}. {script}")
    else:
        typer.secho("All script dependencies:", fg=typer.colors.BLUE, bold=True)
        for name, data in scripts.items():
            depends = data.get("depends", [])
            if depends:
                typer.echo(f"  {name} → {', '.join(depends)}")


def debug_plugins_command() -> None:
    """Debug plugin loading and registration."""
    from ginx.plugins import get_plugin_manager

    typer.secho("Plugin Debug Information:", fg=typer.colors.BLUE, bold=True)

    plugin_manager = get_plugin_manager()
    plugins = plugin_manager.list_plugins()
    typer.echo(f"Registered plugins: {len(plugins)}")

    for name, plugin in plugins.items():
        typer.secho(f"  ✓ {name}", fg=typer.colors.GREEN)
        typer.echo(f"    Version: {plugin.version}")
        typer.echo(f"    Description: {plugin.description}")

    if not plugins:
        typer.secho("  No plugins registered", fg=typer.colors.YELLOW)
