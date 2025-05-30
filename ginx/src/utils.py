"""
Utility functions for Ginx CLI tool.
"""

import os
import platform
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

from ginx.src.constants import (
    COMMON_PROJECT_ROOT_MARKERS,
    DANGEROUS_PATTERNS,
    DEFAULT_REQUIREMENTS_FILES,
)
from ginx.src.loader import get_global_config


def get_shell() -> str:
    """
    Get the current shell being used.

    Returns:
        Shell name (bash, zsh, fish, cmd, powershell, etc.)
    """
    if platform.system() == "Windows":
        return os.environ.get("COMSPEC", "cmd").split("\\")[-1].lower()
    else:
        shell = os.environ.get("SHELL", "/bin/bash")
        return shell.split("/")[-1]


def detect_virtual_environment() -> Dict[str, Any]:
    """Detect if we're in a virtual environment and return info about it."""
    info: Dict[str, Any] = {
        "in_venv": False,
        "venv_type": None,
        "venv_path": None,
        "pip_target": None,
    }

    # Check for virtual environment
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        info["in_venv"] = True
        info["venv_path"] = sys.prefix

        # Detect venv type
        if "conda" in sys.prefix.lower() or "anaconda" in sys.prefix.lower():
            info["venv_type"] = "conda"
        elif "venv" in sys.prefix or "virtualenv" in sys.prefix:
            info["venv_type"] = "venv"
        else:
            info["venv_type"] = "unknown"

    return info


def suggest_virtual_environment():
    """Suggest creating a virtual environment."""
    typer.secho("\n💡 Recommendation: Use a virtual environment", fg=typer.colors.CYAN)
    typer.echo("Create one with:")
    typer.echo("  python -m venv .venv")
    typer.echo("  source .venv/bin/activate  # Linux/Mac")
    typer.echo("  .venv\\Scripts\\activate     # Windows")
    typer.echo("  ginx install-deps --script-deps")


def expand_variables(command: str, env_vars: Optional[Dict[str, str]] = None) -> str:
    """
    Expand environment variables in command string.

    Args:
        command: Command string that may contain environment variables
        env_vars: Additional environment variables to use for expansion

    Returns:
        Command string with expanded variables
    """
    if env_vars:
        # Create a copy of os.environ and update with additional vars
        expanded_env = os.environ.copy()
        expanded_env.update(env_vars)

        # Expand variables
        for key, value in expanded_env.items():
            command = command.replace(f"${key}", value)
            command = command.replace(f"${{{key}}}", value)
            if platform.system() == "Windows":
                command = command.replace(f"%{key}%", value)

    return os.path.expandvars(command)


def validate_command(command: str) -> bool:
    """
    Basic validation of command string.

    Args:
        command: Command to validate

    Returns:
        True if command appears valid, False otherwise
    """
    if not command or not command.strip():
        return False

    command_lower = command.lower()
    global_config = get_global_config()

    if not global_config.get("dangerous_commands", False):
        for pattern in DANGEROUS_PATTERNS:
            if pattern in command_lower:
                typer.secho(
                    f"Warning: Command contains potentially dangerous pattern: {pattern}",
                    fg=typer.colors.YELLOW,
                )
                typer.secho(
                    "\nSet 'dangerous_commands' to true in config to allow this.\n",
                    fg=typer.colors.BLUE,
                )
                return False
    else:
        for pattern in DANGEROUS_PATTERNS:
            if pattern in command_lower:
                typer.secho(
                    f"Warning: Command contains potentially dangerous pattern: {pattern}",
                    fg=typer.colors.YELLOW,
                )
                typer.secho(
                    "\nThis command is allowed because 'dangerous_commands' is enabled in config.\n",
                    fg=typer.colors.BLUE,
                )
                return True

    return True


def run_command_with_streaming(
    command: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None
) -> int:
    """
    Run a command with real-time output streaming.

    Args:
        command: Command and arguments as a list
        cwd: Working directory to run the command in
        env: Environment variables

    Returns:
        Exit code of the command
    """
    process = None
    try:
        # Merge environment variables
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=full_env,
            bufsize=1,
        )

        # Stream output in real-time
        if process.stdout is not None:
            for line in iter(process.stdout.readline, ""):
                typer.echo(line.rstrip())

        process.wait()
        return process.returncode

    except KeyboardInterrupt:
        typer.secho("\nCommand interrupted by user", fg=typer.colors.YELLOW)
        if process:
            process.terminate()
        return 130
    except Exception as e:
        typer.secho(f"Error running command: {e}", fg=typer.colors.RED)
        return 1


def run_command_with_streaming_shell(
    command: str, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None
) -> int:
    """
    Run a shell command with real-time output streaming.

    Args:
        command: Command string to execute through shell
        cwd: Working directory to run the command in
        env: Environment variables

    Returns:
        Exit code of the command
    """
    process = None
    try:
        # Merge environment variables
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=full_env,
            bufsize=1,
        )

        # Stream output in real-time
        if process.stdout is not None:
            for line in iter(process.stdout.readline, ""):
                typer.echo(line.rstrip())

        process.wait()
        return process.returncode

    except KeyboardInterrupt:
        typer.secho("\nCommand interrupted by user", fg=typer.colors.YELLOW)
        if process:
            process.terminate()
        return 130
    except Exception as e:
        typer.secho(f"Error running command: {e}", fg=typer.colors.RED)
        return 1


def extract_commands_from_shell_string(command_str: str) -> set[str]:
    """
    Extract all command names from a shell command string with operators.

    Handles quoted strings properly - operators inside quotes are not treated as separators.

    Examples:
        'echo "hello && world" && ls' -> {'echo', 'ls'}
        "grep 'pattern|pipe' | sort" -> {'grep', 'sort'}
        'cd "$HOME" && pwd' -> {'cd', 'pwd'}
    """
    commands: set[str] = set()

    # Shell operators that separate commands
    shell_operators = ["&&", "||", ";", "|"]

    def parse_shell_command(cmd_str: str) -> List[str]:
        """Parse shell command respecting quotes and escaping."""
        parts: List[str] = []
        current_part = ""
        i = 0
        in_single_quote = False
        in_double_quote = False

        while i < len(cmd_str):
            char = cmd_str[i]

            # Handle escape sequences
            if char == "\\" and i + 1 < len(cmd_str):
                if in_single_quote:
                    # In single quotes, backslash is literal
                    current_part += char
                else:
                    # In double quotes or unquoted, backslash escapes next char
                    current_part += cmd_str[i + 1]
                    i += 1  # Skip the escaped character
                i += 1
                continue

            # Handle quote state changes
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                current_part += char
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                current_part += char
            # Check for operators only when not in quotes
            elif not in_single_quote and not in_double_quote:
                # Check if we're at the start of an operator
                operator_found = None
                for op in shell_operators:
                    if cmd_str[i : i + len(op)] == op:
                        # Make sure it's a complete operator (not part of a longer string)
                        if (
                            i + len(op) >= len(cmd_str)
                            or cmd_str[i + len(op)] in " \t\n"
                            or any(
                                cmd_str[i + len(op) : i + len(op) + len(other_op)]
                                == other_op
                                for other_op in shell_operators
                            )
                        ):
                            operator_found = op
                            break

                if operator_found:
                    # Found an operator outside quotes
                    if current_part.strip():
                        parts.append(current_part.strip())
                    current_part = ""
                    i += len(operator_found)
                    continue
                else:
                    current_part += char
            else:
                # Inside quotes, add character as-is
                current_part += char

            i += 1

        # Add the last part
        if current_part.strip():
            parts.append(current_part.strip())

        return parts

    # Parse the command into parts, respecting quotes
    command_parts = parse_shell_command(command_str)

    # Extract the first word (command name) from each part
    for part in command_parts:
        if not part:
            continue

        try:
            # Use shlex to properly handle quotes and get the actual command
            words = shlex.split(part)
            if words:
                command_name = words[0]
                # Skip relative paths and add valid command names
                if not command_name.startswith("./") and not command_name.startswith(
                    "../"
                ):
                    commands.add(command_name)
        except ValueError:
            # If shlex fails, fall back to simple splitting
            words = part.split()
            if words:
                command_name = words[0].strip("\"'")  # Remove surrounding quotes
                if not command_name.startswith("./") and not command_name.startswith(
                    "../"
                ):
                    commands.add(command_name)

    return commands


def check_dependencies(required_commands: List[str]) -> Dict[str, bool]:
    """
    Check if required commands are available in the system.

    Args:
        required_commands: List of command names to check

    Returns:
        Dictionary mapping command names to availability status
    """
    results: Dict[str, bool] = {}

    for cmd in required_commands:
        try:
            # Use 'which' on Unix-like systems, 'where' on Windows
            check_cmd = "where" if platform.system() == "Windows" else "which"
            subprocess.run(
                [check_cmd, cmd],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            results[cmd] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            results[cmd] = False

    return results


def get_project_root() -> Optional[Path]:
    """
    Find the project root directory by looking for common markers.

    Returns:
        Path to project root if found, None otherwise
    """
    current = Path.cwd()

    for directory in [current] + list(current.parents):
        for marker in COMMON_PROJECT_ROOT_MARKERS:
            if (directory / marker).exists():
                return directory

    return None


def format_duration(seconds: float) -> str:
    """
    Format duration in a human-readable way.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 1:
        return f"{seconds:.2f}s"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def safe_filename(filename: str) -> str:
    """
    Convert a string to a safe filename by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Safe filename
    """
    # Characters not allowed in filenames
    invalid_chars = '<>:"/\\|?*'

    safe_name = filename
    for char in invalid_chars:
        safe_name = safe_name.replace(char, "_")

    # Remove leading/trailing whitespace and dots
    safe_name = safe_name.strip(" .")

    # Ensure it's not empty
    if not safe_name:
        safe_name = "unnamed"

    return safe_name


def colorize_output(text: str, success: bool = True) -> str:
    """
    Add color codes to text based on success/failure.

    Args:
        text: Text to colorize
        success: Whether this represents success (green) or failure (red)

    Returns:
        Colorized text
    """
    if success:
        return typer.style(text, fg=typer.colors.GREEN)
    else:
        return typer.style(text, fg=typer.colors.RED)


def find_requirements_files() -> List[str]:
    """Find available requirements files in the project."""
    found_files: List[str] = []
    for req_file in DEFAULT_REQUIREMENTS_FILES:
        if os.path.exists(req_file):
            found_files.append(req_file)
    return found_files


def parse_requirements_file(file_path: str) -> List[str]:
    """Parse a requirements file and return list of packages."""
    packages: List[str] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith("#") and not line.startswith("-"):
                    # Handle package names with version specifiers
                    package_name = (
                        line.split("==")[0]
                        .split(">=")[0]
                        .split("<=")[0]
                        .split("~=")[0]
                        .split(">")[0]
                        .split("<")[0]
                        .strip()
                    )
                    if package_name:
                        packages.append(
                            line
                        )  # Keep full specification for installation
    except Exception as e:
        typer.secho(
            f"Warning: Could not parse {file_path}: {e}", fg=typer.colors.YELLOW
        )
    return packages


def parse_command_with_extras(command_template: str, extra_input: str = "") -> str:
    """
    Parse command template with EXTRA_[DATATYPE] placeholders

    Supported placeholders:
    - EXTRA_STRING: Quoted string argument
    - EXTRA_RAW: Raw unquoted argument
    - EXTRA_NUMBER: Numeric argument
    - EXTRA_ARGS: Multiple arguments (split by spaces)
    """

    extra_pattern: str = r"EXTRA_([A-Z_]+)"
    placeholders = re.findall(extra_pattern, command_template)

    if not placeholders and extra_input:
        typer.secho(
            "Warning: Extra input provided but no EXTRA_ placeholder found",
            fg=typer.colors.YELLOW,
        )
        return command_template

    if placeholders and not extra_input:
        typer.secho(
            "Error: Command requires extra input but none provided", fg=typer.colors.RED
        )
        raise typer.Exit(code=1)

    processed_command: str = command_template

    for placeholder_type in placeholders:
        placeholder = f"EXTRA_{placeholder_type}"

        if placeholder_type == "STRING":
            # Handle as quoted string - preserve as single argument
            replacement = shlex.quote(extra_input.strip())

        elif placeholder_type == "RAW":
            # Handle as raw input - no quoting
            replacement = extra_input.strip()

        elif placeholder_type == "NUMBER":
            # Validate as number
            try:
                float(extra_input.strip())
                replacement = extra_input.strip()
            except ValueError:
                typer.secho(
                    f"Error: Expected number but got '{extra_input}'",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(code=1)

        elif placeholder_type == "ARGS":
            # Split into multiple arguments
            try:
                args = shlex.split(extra_input)
                replacement = " ".join(shlex.quote(arg) for arg in args)
            except ValueError as e:
                typer.secho(f"Error parsing arguments: {e}", fg=typer.colors.RED)
                raise typer.Exit(code=1)

        else:
            typer.secho(
                f"Error: Unknown placeholder type EXTRA_{placeholder_type}",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)

        processed_command = processed_command.replace(placeholder, replacement)

    return processed_command


def parse_command_and_extra(
    command_str: str, extra: Optional[str] = None, needs_shell: bool = False
):
    """Parse command with optional EXTRA_ placeholder support"""

    if "EXTRA_" in command_str:
        # Process template with extra input
        try:
            processed_command_str = parse_command_with_extras(
                command_str, str(extra) if extra else ""
            )
        except typer.Exit:
            raise

        # Parse the processed command
        if needs_shell:
            full_command = processed_command_str
            command_display = processed_command_str
        else:
            try:
                full_command = shlex.split(processed_command_str)
                command_display = " ".join(full_command)
            except ValueError as e:
                typer.secho(
                    f"Error parsing processed command: {e}", fg=typer.colors.RED
                )
                raise typer.Exit(code=1)
    else:
        if needs_shell:
            full_command = command_str + (" " + extra if extra else "")
            command_display = full_command
        else:
            try:
                command = shlex.split(command_str) + (shlex.split(extra) if extra else [])
                full_command = command
                command_display = " ".join(command)

            except ValueError as e:
                typer.secho(f"Error parsing command: {e}", fg=typer.colors.RED)
                raise typer.Exit(code=1)

    return full_command, command_display
