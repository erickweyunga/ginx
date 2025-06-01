"""
Core script execution logic.
"""

import shlex
import subprocess
import time
from typing import Any, Dict

import typer

from ginx.config import get_scripts
from ginx.utils import (
    expand_variables,
    extract_commands_from_shell_string,
    format_duration,
    parse_command_and_extra,
    run_command_with_streaming,
    run_command_with_streaming_shell,
    validate_command,
)


def execute_script_logic(
    script_name: str,
    script_config: Dict[str, Any],
    extra: str,
    streaming: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    """
    Core script execution logic with enhanced variable support.

    Args:
        script_name: Name of the script to execute
        script_config: Script configuration dictionary
        extra: Extra CLI arguments
        streaming: Whether to stream output
        dry_run: Whether to perform a dry run
        verbose: Whether to show verbose output
    """
    scripts = get_scripts()
    if script_name not in scripts:
        typer.secho(f"Script '{script_name}' not found.", fg=typer.colors.RED)
        typer.echo("\nAvailable scripts:")
        for name in scripts.keys():
            typer.echo(f"  - {name}")
        raise typer.Exit(code=1)

    script = scripts[script_name]
    command_str = script["command"]

    # Expand environment variables
    script_env = script.get("env", {})
    command_str = expand_variables(command_str, script_env)

    # Validate command
    if not validate_command(command_str):
        typer.secho("Command validation failed. Aborting.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Check if command contains shell operators or builtins
    shell_operators = ["&&", "||", ";", "|", ">", "<", "&", "$(", "`"]
    shell_builtins = [
        "cd",
        "export",
        "set",
        "unset",
        "alias",
        "source",
        ".",
        "eval",
        "exec",
    ]

    needs_shell = any(op in command_str for op in shell_operators)

    if not needs_shell:
        # Check for shell builtins in the command
        command = extract_commands_from_shell_string(command_str)
        for cmd in command:
            if cmd in shell_builtins:
                needs_shell = True
                break

    # Parse command and add extra arguments
    full_command, command_display = parse_command_and_extra(
        command_str, extra, needs_shell=needs_shell
    )

    if verbose:
        typer.secho(f"Script: {script_name}", fg=typer.colors.BLUE)
        typer.secho(
            f"Description: {script.get('description', 'N/A')}", fg=typer.colors.BLUE
        )
        typer.secho(
            f"Working directory: {script.get('cwd', 'current')}", fg=typer.colors.BLUE
        )
        typer.secho(
            f"Shell mode: {'Yes' if needs_shell else 'No'}", fg=typer.colors.BLUE
        )

    typer.secho(f"Running: {command_display}", fg=typer.colors.CYAN)

    if dry_run:
        typer.secho("Dry run - command not executed", fg=typer.colors.YELLOW)
        return

    _execute_command(
        full_command=full_command,
        needs_shell=needs_shell,
        streaming=streaming,
        script=script,
        script_name=script_name,
        start_time=time.time(),
    )


def _execute_command(
    full_command: str | list[str],
    needs_shell: bool,
    streaming: bool,
    script: Dict[str, Any],
    script_name: str,
    start_time: float,
) -> None:
    """Execute the actual command with proper error handling."""

    try:
        if streaming:
            # Use streaming output
            if needs_shell:
                exit_code = run_command_with_streaming_shell(
                    (
                        str(full_command)
                        if isinstance(full_command, list)
                        else full_command
                    ),
                    cwd=script.get("cwd"),
                    env=script.get("env"),
                )
            else:
                exit_code = run_command_with_streaming(
                    (
                        full_command
                        if isinstance(full_command, list)
                        else shlex.split(full_command)
                    ),
                    cwd=script.get("cwd"),
                    env=script.get("env"),
                )

            if exit_code == 0:
                duration = time.time() - start_time
                typer.secho(
                    f"\n✓ Script completed successfully in {format_duration(duration)}",
                    fg=typer.colors.GREEN,
                )
            else:
                typer.secho(
                    f"\n✗ Script failed with exit code {exit_code}", fg=typer.colors.RED
                )
                raise typer.Exit(code=exit_code)
        else:
            # Capture output
            if needs_shell:
                result = subprocess.run(
                    full_command,
                    shell=True,
                    check=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    cwd=script.get("cwd"),
                    env=script.get("env"),
                )
            else:
                result = subprocess.run(
                    full_command,
                    check=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    cwd=script.get("cwd"),
                    env=script.get("env"),
                )

            duration = time.time() - start_time

            if result.stdout:
                typer.echo(result.stdout)

            typer.secho(
                f"✓ Script completed successfully in {format_duration(duration)}",
                fg=typer.colors.GREEN,
            )

    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        typer.secho(
            f"\n✗ Script execution failed after {format_duration(duration)}",
            fg=typer.colors.RED,
        )

        if e.stderr:
            typer.echo("Error output:")
            typer.echo(e.stderr)
        elif hasattr(e, "output") and e.output:
            typer.echo("Output:")
            typer.echo(e.output)

        raise typer.Exit(code=e.returncode)
    except KeyboardInterrupt:
        duration = time.time() - start_time
        typer.secho(
            f"\n⚠ Script interrupted after {format_duration(duration)}",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=130)
