"""
Core plugin class for version synchronization.
"""

import typer

from ginx.plugins import GinxPlugin

from .commands import (
    CheckUpdatesCommand,
    PinVersionsCommand,
    SyncVersionsCommand,
    VersionDiffCommand,
)
from .version_utils import has_packaging_library


class VersionSyncPlugin(GinxPlugin):
    """Plugin for version synchronization and update checking."""

    def __init__(self):
        self.check_updates_cmd = CheckUpdatesCommand()
        self.sync_versions_cmd = SyncVersionsCommand()
        self.version_diff_cmd = VersionDiffCommand()
        self.pin_versions_cmd = PinVersionsCommand()

    @property
    def name(self) -> str:
        return "version-sync"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Package version synchronization and update checking"

    def initialize(self) -> None:
        """Initialize the plugin."""
        if not has_packaging_library():
            typer.secho(
                "Warning: 'packaging' library not found. Some version comparison features may not work.",
                fg=typer.colors.YELLOW,
            )

    def add_commands(self, app: typer.Typer) -> None:
        """Add version-related commands to the CLI."""

        @app.command(
            "check-updates", help="Check for package updates available on PyPI."
        )
        def check_updates(  # type: ignore
            requirements_file: str = typer.Option(
                "", "--requirements", "-r", help="Specific requirements file to check"
            ),
            show_all: bool = typer.Option(
                False, "--all", help="Show all packages, not just outdated ones"
            ),
            json_output: bool = typer.Option(
                False, "--json", help="Output results in JSON format"
            ),
            timeout: int = typer.Option(
                10, "--timeout", help="Timeout for PyPI requests in seconds"
            ),
        ):
            """Check for package updates from PyPI."""
            self.check_updates_cmd.execute(
                requirements_file, show_all, json_output, timeout
            )

        @app.command(
            "sync-versions",
            help="Sync package versions with PyPI or requirements file.",
        )
        def sync_versions(  # type: ignore
            target: str = typer.Option(
                "latest",
                "--target",
                help="Sync target: latest, requirements, or specific file",
            ),
            requirements_file: str = typer.Option(
                "", "--requirements", "-r", help="Requirements file to sync with"
            ),
            dry_run: bool = typer.Option(
                False,
                "--dry-run",
                "-n",
                help="Show what would be updated without updating",
            ),
            yes: bool = typer.Option(False, "--yes", "-y", help="Auto-confirm updates"),
        ):
            """Sync package versions with PyPI or requirements file."""
            self.sync_versions_cmd.execute(target, requirements_file, dry_run, yes)

        @app.command(
            "version-diff", help="Compare package versions between environments."
        )
        def version_diff(  # type: ignore
            file1: str = typer.Option(..., "--file1", help="First requirements file"),
            file2: str = typer.Option(..., "--file2", help="Second requirements file"),
            show_all: bool = typer.Option(
                False, "--all", help="Show all packages, not just differences"
            ),
        ):
            """Compare package versions between two requirements files."""
            self.version_diff_cmd.execute(file1, file2, show_all)

        @app.command("pin-versions", help="Pin all packages to specific versions.")
        def pin_versions(  # type: ignore
            requirements_file: str = typer.Option(
                "", "--requirements", "-r", help="Requirements file to pin"
            ),
            output_file: str = typer.Option(
                "", "--output", "-o", help="Output file for pinned requirements"
            ),
            force: bool = typer.Option(
                False, "--force", help="Overwrite existing output file"
            ),
        ):
            """Pin all packages to their currently installed versions."""
            self.pin_versions_cmd.execute(requirements_file, output_file, force)
