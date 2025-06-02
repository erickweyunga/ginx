"""
Command execution, validation, and parsing utilities.
"""

import os
import platform
import re
import shlex
import subprocess
import typing
from typing import Any, Dict, List, Optional

import typer

from ginx.config import get_global_config
from ginx.constants import DANGEROUS_PATTERNS


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
                    "This command is allowed because 'dangerous_commands' is enabled in config.",
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
        typer.secho(f"✗ Error running command: {e}", fg=typer.colors.RED)
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


def extract_commands_from_shell_string(command_str: str) -> typing.Set[str]:
    """
    Extract all command names from a shell command string with operators.

    Handles quoted strings properly - operators inside quotes are not treated as separators.

    Examples:
        'echo "hello && world" && ls' -> {'echo', 'ls'}
        "grep 'pattern|pipe' | sort" -> {'grep', 'sort'}
        'cd "$HOME" && pwd' -> {'cd', 'pwd'}
    """
    commands: typing.Set[str] = set()

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


def parse_command_with_extras(command_template: str, extra_input: str = "") -> str:
    """
    Parse command template with ${variable:type} syntax supporting multiple variables.

    Supported placeholders (type is required):
    - ${variable:string}: Quoted string variable
    - ${variable:raw}: Raw variable (no quoting)
    - ${variable:number}: Numeric variable (validated)
    - ${variable:args}: Multiple arguments (consumes remaining args intelligently)

    """

    # Handle ${variable:type} syntax
    variable_pattern: str = r"\$\{([^}]+)\}"
    variables = re.findall(variable_pattern, command_template)

    if not variables and extra_input:
        typer.secho(
            "Warning: Extra input provided but no variable placeholder found",
            fg=typer.colors.YELLOW,
        )
        return command_template

    if variables and not extra_input:
        typer.secho(
            "✗ Error: Command requires extra input but none provided",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    # Parse variable names and types first
    parsed_variables: List[Any] = []
    replacement = ""

    for variable in variables:
        if ":" not in variable:
            typer.secho(
                f"✗ Error: Variable type required. Use ${{{variable}:string}} instead of ${{{variable}}}",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)

        var_name, var_type = variable.split(":", 1)

        if var_type not in ["string", "raw", "number", "args"]:
            typer.secho(
                f"✗ Error: Unsupported variable type '{var_type}' for variable '{var_name}'. Use: string, raw, number, or args",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)

        parsed_variables.append((var_name, var_type, variable))

    processed_command: str = command_template

    # Handle single variable case (use entire input)
    if len(parsed_variables) == 1:
        var_name, var_type, variable = parsed_variables[0]
        placeholder = f"${{{variable}}}"

        # Process the entire input for single variable
        if var_type == "string":
            # Double-quoted string - escape internal quotes
            escaped_input = extra_input.strip().replace('"', '\\"')
            replacement = f'"{escaped_input}"'
        elif var_type == "raw":
            # Raw unquoted input
            replacement = extra_input.strip()
        elif var_type == "number":
            # Validate numeric input
            try:
                float(extra_input.strip())
                replacement = extra_input.strip()
            except ValueError:
                typer.secho(
                    f"✗ Error: Expected number for variable '{var_name}' but got '{extra_input}'",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(code=1)
        elif var_type == "args":
            # Multiple arguments - split the input
            try:
                args = shlex.split(extra_input)
                replacement = " ".join(shlex.quote(arg) for arg in args)
            except ValueError as e:
                typer.secho(
                    f"✗ Error parsing arguments for variable '{var_name}': {e}",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(code=1)

        processed_command = processed_command.replace(placeholder, replacement)
        return processed_command

    # Handle multiple variables case (split input into arguments)
    try:
        input_args = shlex.split(extra_input) if extra_input else []
    except ValueError as e:
        typer.secho(f"✗ Error parsing input arguments: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Calculate minimum required arguments
    non_args_count = sum(1 for _, var_type, _ in parsed_variables if var_type != "args")

    # We need at least as many arguments as non-args variables
    if len(input_args) < non_args_count:
        typer.secho(
            f"✗ Error: Expected at least {non_args_count} arguments for non-args variables, got {len(input_args)}",
            fg=typer.colors.RED,
        )
        typer.secho(
            f"  Variables: {', '.join([f'{name}:{vtype}' for name, vtype, _ in parsed_variables])}",
            fg=typer.colors.BLUE,
        )
        typer.secho(
            f"  Provided: {', '.join(input_args) if input_args else '(none)'}",
            fg=typer.colors.BLUE,
        )
        raise typer.Exit(code=1)

    # Assign arguments to variables intelligently
    arg_index = 0

    for i, (var_name, var_type, variable) in enumerate(parsed_variables):
        placeholder: str = f"${{{variable}}}"

        if var_type == "args":
            # For args type, calculate how many arguments it should consume
            # remaining_vars = len(parsed_variables) - i - 1
            remaining_non_args = sum(
                1 for _, vt, _ in parsed_variables[i + 1 :] if vt != "args"
            )

            # Args variable gets all remaining arguments except what's needed for subsequent non-args vars
            available_args = len(input_args) - arg_index
            args_to_consume = max(0, available_args - remaining_non_args)

            if args_to_consume == 0:
                # No arguments available for this args variable
                replacement = ""
            else:
                consumed_args = input_args[arg_index : arg_index + args_to_consume]
                replacement = " ".join(shlex.quote(arg) for arg in consumed_args)
                arg_index += args_to_consume
        else:
            # Non-args variables consume exactly one argument
            if arg_index >= len(input_args):
                typer.secho(
                    f"✗ Error: Not enough arguments for variable '{var_name}' (type: {var_type})",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(code=1)

            current_input = input_args[arg_index]
            arg_index += 1

            # Process based on type
            if var_type == "string":
                # Double-quoted string - escape internal quotes
                escaped_input = current_input.strip().replace('"', '\\"')
                replacement = f'"{escaped_input}"'
            elif var_type == "raw":
                # Raw unquoted input
                replacement = current_input.strip()
            elif var_type == "number":
                # Validate numeric input
                try:
                    float(current_input.strip())
                    replacement = current_input.strip()
                except ValueError:
                    typer.secho(
                        f"✗ Error: Expected number for variable '{var_name}' but got '{current_input}'",
                        fg=typer.colors.RED,
                    )
                    raise typer.Exit(code=1)

        processed_command = processed_command.replace(placeholder, replacement)

    return processed_command


def parse_command_and_extra(
    command_str: str, extra: Optional[str] = None, needs_shell: bool = False
):
    """Parse command with ${variable} placeholder support for multiple variables"""

    if "${" in command_str:
        try:
            processed_command_str = parse_command_with_extras(
                command_str, str(extra) if extra else ""
            )
        except typer.Exit:
            raise

        if needs_shell:
            full_command = processed_command_str
            command_display = processed_command_str
        else:
            try:
                full_command = shlex.split(processed_command_str)
                command_display = (
                    processed_command_str  # Keep processed string for display
                )
            except ValueError as e:
                typer.secho(
                    f"✗ Error parsing processed command: {e}", fg=typer.colors.RED
                )
                raise typer.Exit(code=1)
    else:
        # No variables - handle as regular command with extra args
        if needs_shell:
            full_command = command_str + (" " + extra if extra else "")
            command_display = full_command
        else:
            try:
                command = shlex.split(command_str) + (
                    shlex.split(extra) if extra else []
                )
                full_command = command
                command_display = " ".join(command)

            except ValueError as e:
                typer.secho(f"✗ Error parsing command: {e}", fg=typer.colors.RED)
                raise typer.Exit(code=1)

    return full_command, command_display
