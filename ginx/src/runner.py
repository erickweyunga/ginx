"""
Main CLI runner for Ginx - Run project scripts defined in a YAML file.
"""

import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import typer

from ginx.src.cmd import COMMANDS
from ginx.src.constants import COMMON_DEV_PACKAGES, DEFAULT_REQUIREMENTS_FILES
from ginx.src.loader import create_sample_config, get_global_config, get_scripts
from ginx.src.plugins import get_plugin_manager
from ginx.src.utils import (
    check_dependencies,
    detect_virtual_environment,
    expand_variables,
    extract_commands_from_shell_string,
    find_requirements_files,
    format_duration,
    parse_command_and_extra,
    parse_requirements_file,
    run_command_with_streaming,
    run_command_with_streaming_shell,
    suggest_virtual_environment,
    validate_command,
)

app = typer.Typer(
    help="Ginx - Run project scripts defined in a YAML file.",
    invoke_without_command=True,
    add_completion=True,
    rich_help_panel="Commands",
)

# Initialize plugin manager
plugin_manager = get_plugin_manager()

# Auto Register built-in plugins
try:
    from ginx.src.plugins import auto_register_builtin_plugins

    auto_register_builtin_plugins()
except Exception:
    pass

# Discover and load external plugins
try:
    plugin_manager.discover_plugins()
except Exception:
    pass

# Add plugin commands to the app
try:
    plugin_manager.add_plugin_commands(app)
except Exception:
    pass


def create_script_command(script_name: str, script_config: Dict[str, Any]):
    def script_command(
        extra: str = typer.Argument("", help="Extra CLI arguments"),
        streaming: bool = typer.Option(
            True, "--stream/--no-stream", help="Stream output"
        ),
        dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Dry run"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    ):
        return execute_script_logic(
            script_name, script_config, extra, streaming, dry_run, verbose
        )

    script_command.__name__ = f"script_{script_name}"
    script_command.__doc__ = script_config.get(
        "description", f"Run {script_name} script"
    )
    return script_command


def register_script_commands():
    try:
        scripts = get_scripts()
        existing_commands = COMMANDS
        for script_name, script_config in scripts.items():
            if script_name not in existing_commands:
                script_command = create_script_command(script_name, script_config)
                app.command(script_name, help=script_config.get("description"))(
                    script_command
                )
    except Exception as e:
        typer.echo(f"Warning: Could not load scripts: {e}")


@app.callback()
def main(ctx: typer.Context):
    """
    Ginx is a command-line script runner powered by YAML configuration.

    Define your scripts in a YAML file and run them directly by name.

    Examples:
        ginx format              # Run the format script
        ginx build --verbose     # Run build script with verbose output
        ginx commit "fix: bug"   # Run commit script with extra args
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())

        raise typer.Exit()


@app.command("version", help="Show Ginx version.")
def show_version():
    """Show the current version of Ginx."""
    try:
        from ginx.src import __version__

        typer.echo(f"Ginx version {__version__}")
    except ImportError:
        typer.echo("Version information not available")


@app.command("list", help="List all available scripts.")
def list_scripts():
    """Displays all scripts from the YAML configuration."""
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


def execute_script_logic(
    script_name: str,
    script_config: Dict[str, Any],
    extra: str,
    streaming: bool,
    dry_run: bool,
    verbose: bool,
):
    """
    Runs a script defined in the YAML file.

    \b
    Example:
        ginx build
        ginx deploy "--force --region us-west"
        ginx test --stream --verbose
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
            # Check if command is a shell builtin
            if cmd in shell_builtins:
                needs_shell = True

    # Parse command and add extra arguments
    full_command, command_display = parse_command_and_extra(
        command_str, extra, needs_shell=True
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

    start_time = time.time()

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
                    capture_output=not streaming,
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
                    capture_output=not streaming,
                    cwd=script.get("cwd"),
                    env=script.get("env"),
                )

            duration = time.time() - start_time

            if result.stdout and not streaming:
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


@app.command("run", help="Run a script by name.")
def run_script(
    script_name: str,
    extra: str = typer.Argument("", help="Extra CLI arguments"),
    streaming: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Stream output in real-time (default: enabled)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be executed without running"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
):
    """
    Runs a script defined in the YAML file.

    \b
    Example:
        ginx run build
        ginx run deploy "--force --region us-west"
        ginx run test --stream --verbose
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
            # Check if command is a shell builtin
            if cmd in shell_builtins:
                needs_shell = True

    # Parse command and add extra arguments
    full_command, command_display = parse_command_and_extra(
        command_str, extra, needs_shell=True
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

    start_time = time.time()

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
                    capture_output=not streaming,
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
                    capture_output=not streaming,
                    cwd=script.get("cwd"),
                    env=script.get("env"),
                )

            duration = time.time() - start_time

            if result.stdout and not streaming:
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


@app.command("init", help="Create a sample ginx.yaml configuration file.")
def init_config(
    filename: str = typer.Option(
        "ginx.yaml", "--file", "-f", help="Configuration filename"
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing configuration file"
    ),
):
    """Create a sample configuration file with common script examples."""
    import os

    if os.path.exists(filename) and not force:
        typer.secho(
            f"Configuration file '{filename}' already exists. Use --force to overwrite.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    create_sample_config(filename)


@app.command("validate", help="Validate the configuration file.")
def validate_config():
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


@app.command("deps", help="Check dependencies and requirements files.")
def check_script_dependencies():
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
    commands_to_check: set[str] = set()
    for script in scripts.values():
        command = script.get("command", "")
        if command:
            found_commands = extract_commands_from_shell_string(command)
            commands_to_check.update(found_commands)

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
        typer.secho("Install missing dependencies:", fg=typer.colors.CYAN)
        if req_files:
            typer.echo(
                "  ginx install-deps                 # Install from requirements files"
            )
        typer.echo("  ginx install-deps --script-deps   # Install script dependencies")
        typer.echo("  ginx generate-reqs                # Generate requirements file")


@app.command(
    "install-deps",
    help="Install dependencies from requirements files or for missing script commands.",
)
def install_missing_dependencies(
    requirements_file: str = typer.Option(
        "", "--requirements", "-r", help="Specific requirements file to install from"
    ),
    dev_only: bool = typer.Option(
        False, "--dev", help="Install development dependencies only"
    ),
    script_deps: bool = typer.Option(
        False, "--script-deps", help="Install dependencies for script commands"
    ),
    scope: str = typer.Option(
        "auto", "--scope", help="Installation scope: auto, global, user, venv, project"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be installed without installing"
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Install without confirmation prompts"
    ),
    upgrade: bool = typer.Option(
        False, "--upgrade", "-U", help="Upgrade packages if already installed"
    ),
    create_venv: bool = typer.Option(
        False, "--create-venv", help="Create a virtual environment if not in one"
    ),
):
    """
    Install missing dependencies with scope control.

    Scopes:
        auto    - Detect environment and choose best option (default)
        global  - Install to global Python environment
        user    - Install to user site-packages (--user)
        venv    - Install to virtual environment (error if not in one)
        project - Install to project directory (--target ./venv)

    Examples:
        ginx install-deps --script-deps                    # Auto-detect scope
        ginx install-deps --script-deps --scope user       # Install to user directory
        ginx install-deps --script-deps --scope project    # Install to ./venv
        ginx install-deps --script-deps --create-venv      # Create venv first
    """
    # Detect current environment
    venv_info = detect_virtual_environment()
    global_config = get_global_config()

    # Handle virtual environment creation
    if create_venv and not venv_info["in_venv"]:
        typer.secho("Creating virtual environment...", fg=typer.colors.BLUE)
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
            typer.secho("✓ Virtual environment created at .venv", fg=typer.colors.GREEN)
            typer.echo("Activate it with:")
            typer.echo("  source .venv/bin/activate  # Linux/Mac")
            typer.echo("  .venv\\Scripts\\activate     # Windows")
            typer.echo("Then run the install command again.")
            return
        except subprocess.CalledProcessError:
            typer.secho("✗ Failed to create virtual environment", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    # Determine installation scope
    pip_args: List[str] = []
    scope_description = ""

    if scope == "auto":
        if venv_info["in_venv"]:
            scope_description = f"virtual environment ({venv_info['venv_type']})"
        else:
            # Default to user scope if not in venv
            pip_args.append("--user")
            scope_description = "user directory"
            typer.secho(
                "⚠ Not in virtual environment, installing to user directory",
                fg=typer.colors.YELLOW,
            )

    elif scope == "global":
        scope_description = "global Python environment"
        if not venv_info["in_venv"]:
            typer.secho(
                "⚠ Installing to global Python environment", fg=typer.colors.YELLOW
            )

    elif scope == "user":
        pip_args.append("--user")
        scope_description = "user directory (~/.local)"

    elif scope == "venv":
        if not venv_info["in_venv"]:
            typer.secho(
                "✗ Not in a virtual environment. Use --create-venv or activate one.",
                fg=typer.colors.RED,
            )
            suggest_virtual_environment()
            raise typer.Exit(code=1)
        scope_description = f"virtual environment ({venv_info['venv_type']})"

    elif scope == "project":
        project_venv: Path = Path("./venv")
        project_venv.mkdir(exist_ok=True)
        pip_args.extend(["--target", str(project_venv)])
        scope_description = f"project directory ({project_venv})"

    else:
        typer.secho(f"✗ Invalid scope: {scope}", fg=typer.colors.RED)
        typer.echo("Valid scopes: auto, global, user, venv, project")
        raise typer.Exit(code=1)

    packages_to_install = []

    if requirements_file:
        # Install from specific requirements file
        if not os.path.exists(requirements_file):
            typer.secho(
                f"Requirements file not found: {requirements_file}", fg=typer.colors.RED
            )
            raise typer.Exit(code=1)

        packages_to_install = parse_requirements_file(requirements_file)
        typer.secho(
            f"Found {len(packages_to_install)} packages in {requirements_file}",
            fg=typer.colors.BLUE,
        )

    elif script_deps:
        # Install dependencies for script commands
        scripts = get_scripts()
        if not scripts:
            typer.secho("No scripts found.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        # Extract missing commands and try to map to packages
        commands_to_check: set[str] = set()
        for script in scripts.values():
            command = script.get("command", "")
            if command:
                found_commands = extract_commands_from_shell_string(command)
                commands_to_check.update(found_commands)

        results = check_dependencies(list(commands_to_check))
        missing_commands = [cmd for cmd, available in results.items() if not available]

        # Filter to common dev packages we know about
        packages_to_install: List[str] = [
            cmd for cmd in missing_commands if cmd in COMMON_DEV_PACKAGES
        ]

        if not packages_to_install:
            typer.secho(
                "No missing script dependencies found that can " "be auto-installed.",
                fg=typer.colors.GREEN,
            )
            return

    else:
        # Auto-detect requirements files
        req_files = find_requirements_files()

        if not req_files:
            typer.secho("No requirements files found.", fg=typer.colors.YELLOW)
            typer.echo("Looking for: " + ", ".join(DEFAULT_REQUIREMENTS_FILES))
            typer.echo("\nTry:")
            typer.echo(
                "  ginx install-deps --script-deps  # Install deps for script commands"
            )
            typer.echo(
                "  ginx generate-reqs               # Generate requirements file"
            )
            return

        # Show found files and let user choose or install all
        typer.secho("Found requirements files:", fg=typer.colors.BLUE)
        for i, file in enumerate(req_files, 1):
            typer.echo(f"  {i}. {file}")

        if dev_only:
            # Filter to dev-related files
            dev_files = [f for f in req_files if "dev" in f.lower()]
            if dev_files:
                req_files = dev_files
                typer.secho(
                    f"Installing from dev files only: {', '.join(dev_files)}",
                    fg=typer.colors.CYAN,
                )

        # Parse all selected files
        for req_file in req_files:
            packages = parse_requirements_file(req_file)
            packages_to_install.extend(packages)
            typer.echo(f"  {req_file}: {len(packages)} packages")

    if not packages_to_install:
        typer.secho("No packages to install.", fg=typer.colors.GREEN)
        return

    # Remove duplicates while preserving order
    packages_to_install = list(dict.fromkeys(packages_to_install))

    typer.secho(f"Installation scope: {scope_description}", fg=typer.colors.CYAN)
    typer.echo(f"Packages to install ({len(packages_to_install)}):")
    for pkg in packages_to_install:
        typer.echo(f"  - {pkg}")

    # Build pip command with scope arguments
    pip_cmd = [sys.executable, "-m", "pip", "install"]
    pip_cmd.extend(pip_args)  # Add scope-specific arguments (--user, --target, etc.)

    if upgrade:
        pip_cmd.append("--upgrade")
    pip_cmd.extend(packages_to_install)

    typer.echo(f"\nCommand: {' '.join(pip_cmd)}")

    if dry_run:
        typer.secho("Dry run - packages not installed", fg=typer.colors.YELLOW)
        return

    # Ask for confirmation with scope warning
    if not global_config.get("dangerous_commands", yes):
        if scope == "global" and not venv_info["in_venv"]:
            typer.secho(
                "⚠ This will install to your global Python environment!",
                fg=typer.colors.RED,
            )

        install_confirm = typer.confirm(
            f"Install {len(packages_to_install)} package(s) to {scope_description}?"
        )
        if not install_confirm:
            typer.echo("Installation cancelled.")
            if not venv_info["in_venv"] and scope != "user":
                suggest_virtual_environment()
            return

    # Install packages
    typer.secho(f"Installing packages to {scope_description}...", fg=typer.colors.BLUE)

    try:
        result = subprocess.run(
            pip_cmd,
            check=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.stdout:
            typer.echo(result.stdout)

        typer.secho("✓ Installation completed successfully!", fg=typer.colors.GREEN)

    except subprocess.CalledProcessError as e:
        typer.secho("✗ Installation failed!", fg=typer.colors.RED)
        if e.stderr:
            typer.echo("Error output:")
            typer.echo(e.stderr)
        raise typer.Exit(code=e.returncode)


@app.command(
    "generate-reqs",
    help="Generate requirements file based on missing dependencies or virtual environment.",
)
def generate_requirements(
    output_file: str = typer.Option(
        "requirements.txt", "--output", "-o", help="Output requirements file"
    ),
    script_deps: bool = typer.Option(
        False, "--script-deps", help="Include dependencies for script commands"
    ),
    from_venv: bool = typer.Option(
        False, "--from-venv", help="Generate from current virtual environment packages"
    ),
    dev_file: bool = typer.Option(
        False,
        "--dev",
        help="Generate development requirements (changes default filename)",
    ),
    exclude_system: bool = typer.Option(
        True,
        "--exclude-system/--include-system",
        help="Exclude system/built-in packages",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing requirements file"
    ),
):
    """
    Generate a requirements file from virtual environment or missing script dependencies.

    Examples:
        ginx generate-reqs --from-venv                    # From current venv
        ginx generate-reqs --from-venv --dev              # Dev requirements from venv
        ginx generate-reqs --script-deps                  # From missing script deps
        ginx generate-reqs --from-venv -o requirements.txt # Custom output file
    """

    # Adjust default filename if dev flag is used
    if dev_file and output_file == "requirements.txt":
        output_file = "requirements-dev.txt"

    if os.path.exists(output_file) and not force:
        typer.secho(
            f"File '{output_file}' already exists. Use --force to overwrite.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    packages_to_add = []

    venv_info: Dict[str, Any] = {}
    if from_venv:
        # Generate from virtual environment
        venv_info = detect_virtual_environment()

        if not venv_info["in_venv"]:
            typer.secho("✗ Not in a virtual environment!", fg=typer.colors.RED)
            suggest_virtual_environment()
            raise typer.Exit(code=1)

        typer.secho(
            f"Generating from virtual environment: {venv_info['venv_type']}",
            fg=typer.colors.BLUE,
        )

        try:
            # Get installed packages using pip freeze
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                check=True,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
            )

            installed_packages = result.stdout.strip().split("\n")

            # Filter packages if needed
            if exclude_system:
                # List of packages typically installed by default/system
                system_packages = {
                    "pip",
                    "setuptools",
                    "wheel",
                    "pip-tools",
                    "distlib",
                    "packaging",
                    "pyparsing",
                    "six",
                    "certifi",
                    "charset-normalizer",
                    "idna",
                    "requests",
                    "urllib3",
                }

                filtered_packages: List[str] = []
                for pkg in installed_packages:
                    if pkg.strip():
                        pkg_name = (
                            pkg.split("==")[0]
                            .split(">=")[0]
                            .split("<=")[0]
                            .strip()
                            .lower()
                        )
                        if pkg_name not in system_packages:
                            filtered_packages.append(pkg)

                packages_to_add = filtered_packages
            else:
                packages_to_add = [pkg for pkg in installed_packages if pkg.strip()]

            typer.secho(
                f"Found {len(packages_to_add)} packages in virtual environment",
                fg=typer.colors.GREEN,
            )

        except subprocess.CalledProcessError as e:
            typer.secho("✗ Failed to get installed packages", fg=typer.colors.RED)
            if e.stderr:
                typer.echo(f"Error: {e.stderr}")
            raise typer.Exit(code=1)

    elif script_deps:
        # Generate from missing script dependencies (existing logic)
        scripts = get_scripts()
        if scripts:
            commands_to_check: set[str] = set()
            for script in scripts.values():
                command = script.get("command", "")
                if command:
                    found_commands = extract_commands_from_shell_string(command)
                    commands_to_check.update(found_commands)

            results = check_dependencies(list(commands_to_check))
            missing_commands = [
                cmd for cmd, available in results.items() if not available
            ]

            # Filter to known packages
            packages_to_add = [
                cmd for cmd in missing_commands if cmd in COMMON_DEV_PACKAGES
            ]

            typer.secho(
                f"Found {len(packages_to_add)} missing script dependencies",
                fg=typer.colors.BLUE,
            )

    else:
        # Default: try both methods
        typer.secho(
            "No generation method specified. Use --from-venv or --script-deps",
            fg=typer.colors.YELLOW,
        )
        typer.echo("\nAvailable options:")
        typer.echo("  --from-venv     Generate from current virtual environment")
        typer.echo("  --script-deps   Generate from missing script dependencies")
        raise typer.Exit(code=1)

    if not packages_to_add:
        if from_venv:
            typer.secho(
                "No packages found in virtual environment.", fg=typer.colors.YELLOW
            )
        else:
            typer.secho(
                "No missing dependencies found to add to requirements.",
                fg=typer.colors.YELLOW,
            )
        return

    # Create requirements file content
    content: List[str] = []

    if from_venv:
        content.extend(
            [
                f"# Generated by Ginx from virtual environment",
                f"# Virtual environment: {venv_info['venv_type']}",
                f"# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"# Install with: pip install -r {output_file}",
                "",
            ]
        )
    else:
        content.extend(
            [
                "# Generated by Ginx - Missing script dependencies",
                f"# Install with: pip install -r {output_file}",
                "",
            ]
        )

    content.extend(packages_to_add)
    content.append("")  # Final newline

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

        typer.secho(
            f"✓ Generated {output_file} with {len(packages_to_add)} packages",
            fg=typer.colors.GREEN,
        )

        if from_venv and len(packages_to_add) > 10:
            typer.echo("First 10 packages:")
            for pkg in packages_to_add[:10]:
                typer.echo(f"  - {pkg}")
            typer.echo(f"  ... and {len(packages_to_add) - 10} more")
        else:
            for pkg in packages_to_add:
                typer.echo(f"  - {pkg}")

        typer.echo(f"\nInstall with: ginx install-deps -r {output_file}")

    except Exception as e:
        typer.secho(f"Error creating requirements file: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("freeze", help="Freeze current virtual environment to requirements file.")
def freeze_environment(
    output_file: str = typer.Option(
        "requirements.txt", "--output", "-o", help="Output requirements file"
    ),
    dev: bool = typer.Option(
        False, "--dev", help="Generate requirements-dev.txt instead"
    ),
    exclude_system: bool = typer.Option(
        True, "--exclude-system/--include-system", help="Exclude common system packages"
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing requirements file"
    ),
):
    """
    Freeze current virtual environment packages to a requirements file.

    This is equivalent to 'pip freeze > requirements.txt' but with additional filtering options.

    Examples:
        ginx freeze                           # Generate requirements.txt
        ginx freeze --dev                     # Generate requirements-dev.txt
        ginx freeze -o my-requirements.txt    # Custom filename
        ginx freeze --include-system          # Include all packages
    """

    if dev and output_file == "requirements.txt":
        output_file = "requirements-dev.txt"

    # Delegate to generate_requirements with from_venv=True
    try:
        generate_requirements(
            output_file=output_file,
            script_deps=False,
            from_venv=True,
            dev_file=dev,
            exclude_system=exclude_system,
            force=force,
        )
    except Exception as e:
        typer.secho(f"Error freezing environment: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("env", help="Show current Python environment information.")
def show_environment():
    """Display information about the current Python environment."""
    import sys

    venv_info = detect_virtual_environment()

    typer.secho("Python Environment Information:", fg=typer.colors.BLUE, bold=True)
    typer.echo(f"Python version: {sys.version}")
    typer.echo(f"Python executable: {sys.executable}")
    typer.echo(f"Python prefix: {sys.prefix}")

    if venv_info["in_venv"]:
        typer.secho(
            f"✓ Virtual environment: {venv_info['venv_type']}", fg=typer.colors.GREEN
        )
        typer.echo(f"  Path: {venv_info['venv_path']}")
    else:
        typer.secho("⚠ Not in virtual environment", fg=typer.colors.YELLOW)
        suggest_virtual_environment()

    # Show site-packages locations
    import site

    typer.echo(f"\nSite packages:")
    for path in site.getsitepackages():
        typer.echo(f"  - {path}")

    if hasattr(site, "getusersitepackages"):
        typer.echo(f"User site packages: {site.getusersitepackages()}")


@app.command("debug-plugins", help="Debug plugin loading status.")
def debug_plugins():
    """Debug plugin loading and registration."""
    typer.secho("Plugin Debug Information:", fg=typer.colors.BLUE, bold=True)

    plugins = plugin_manager.list_plugins()
    typer.echo(f"Registered plugins: {len(plugins)}")

    for name, plugin in plugins.items():
        typer.secho(f"  ✓ {name}", fg=typer.colors.GREEN)
        typer.echo(f"    Version: {plugin.version}")
        typer.echo(f"    Description: {plugin.description}")

    if not plugins:
        typer.secho("  No plugins registered", fg=typer.colors.YELLOW)


register_script_commands()


if __name__ == "__main__":
    app()
