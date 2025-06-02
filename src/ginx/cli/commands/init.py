"""
Init command implementation.
"""

import os

import typer

from ginx.config import create_sample_config


def init_config_command(
    filename: str = typer.Option(
        "ginx.yaml", "--file", "-f", help="Configuration filename"
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing configuration file"
    ),
) -> None:
    """Create a sample configuration file with common script examples."""

    if os.path.exists(filename) and not force:
        typer.secho(
            f"Configuration file '{filename}' already exists. Use --force to overwrite.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    create_sample_config(filename)
