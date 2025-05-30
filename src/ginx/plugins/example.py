from typing import List

import typer

from ginx.plugins import GinxPlugin, get_plugin_manager


class ExamplePlugin(GinxPlugin):
    """Example plugin that demonstrates the plugin system."""

    @property
    def name(self) -> str:
        return "example"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Example plugin for demonstration"

    def add_commands(self, app: typer.Typer) -> None:
        """Add example commands."""

        @app.command("plugin-info", help="Show information about loaded plugins")
        def plugin_info():  # type: ignore
            """Display information about all loaded plugins."""
            plugins = get_plugin_manager().list_plugins()

            if not plugins:
                typer.echo("No plugins loaded.")
                return

            typer.secho("Loaded plugins:", fg=typer.colors.BLUE, bold=True)
            typer.echo()

            for name, plugin in plugins.items():
                typer.secho(f"  {name}", fg=typer.colors.GREEN, bold=True)
                typer.echo(f"    Version: {plugin.version}")
                typer.echo(f"    Description: {plugin.description}")
                typer.echo()

    def pre_execution_hook(self, script_name: str, command: List[str]) -> List[str]:
        """Example pre-execution hook."""
        # This could be used to modify commands, add logging, etc.
        return command

    def post_execution_hook(
        self, script_name: str, exit_code: int, duration: float
    ) -> None:
        """Example post-execution hook."""
        # This could be used for logging, notifications, etc.
        pass


__all__ = [
    "ExamplePlugin",
]
