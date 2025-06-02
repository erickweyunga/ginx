"""
Run command implementation.
"""

import typer

from ginx.cli.execution import execute_script_logic
from ginx.config import get_scripts


def run_script_command(
    script_name: str,
    extra: str = typer.Argument("", help="Extra CLI arguments"),
    streaming: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Stream output in real-time (default: enabled)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be executed without running"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
) -> None:
    """
    Run a script defined in the YAML file.

    \b
    Example:
        ginx run build
        ginx run deploy "staging"
        ginx run commit "fix: bug"
        ginx run test --stream --verbose
    """
    scripts = get_scripts()
    if script_name not in scripts:
        typer.secho(f"Script '{script_name}' not found.", fg=typer.colors.RED)
        typer.echo("\nAvailable scripts:")
        for name in scripts.keys():
            typer.echo(f"  - {name}")
        raise typer.Exit(code=1)

    script_config = scripts[script_name]
    execute_script_logic(script_name, script_config, extra, streaming, dry_run, verbose)
