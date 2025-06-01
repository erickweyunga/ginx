"""
Dynamic script command registration.
"""

from typing import Any, Dict
import typer

from ginx.cli.commands.registry import is_command_reserved
from ginx.config import get_scripts
from ginx.cli.execution import execute_script_logic


def create_script_command(script_name: str, script_config: Dict[str, Any]):
    """Creating a dynamic script command."""

    def script_command(
        extra: str = typer.Argument("", help="Extra CLI arguments"),
        streaming: bool = typer.Option(
            True, "--stream/--no-stream", help="Stream output"
        ),
        dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Dry run"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    ) -> None:
        return execute_script_logic(
            script_name, script_config, extra, streaming, dry_run, verbose
        )

    script_command.__name__ = f"script_{script_name}"
    script_command.__doc__ = script_config.get(
        "description", f"Run {script_name} script"
    )
    return script_command


def register_script_commands(app: typer.Typer) -> None:
    """Register all script commands dynamically."""

    try:
        scripts = get_scripts()

        for script_name, script_config in scripts.items():
            if not is_command_reserved(script_name):
                script_command = create_script_command(script_name, script_config)
                app.command(script_name, help=script_config.get("description"))(
                    script_command
                )
            else:
                pass
    except Exception as e:
        typer.echo(f"Warning: Could not load scripts: {e}")
