"""
Main Ginx - Typer app setup and initialization.
"""

import typer
from ginx.plugins import get_plugin_manager

# Create the main app
app = typer.Typer(
    help="Ginx - Run project scripts defined in a YAML file.",
    invoke_without_command=True,
    add_completion=True,
    rich_help_panel="Commands",
)


def initialize_app() -> typer.Typer:
    """Initialize the Ginx application with plugins and commands."""

    # Initialize plugin manager
    plugin_manager = get_plugin_manager()

    # Auto Register built-in plugins
    try:
        from ginx.plugins import auto_register_builtin_plugins

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

    return app


@app.callback()
def main(ctx: typer.Context) -> None:
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
