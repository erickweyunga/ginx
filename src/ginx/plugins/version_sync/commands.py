"""
Command implementations for version sync plugin.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import typer

from .package_utils import (
    compare_package_sets,
    create_pinned_requirements,
    filter_system_packages,
    get_installed_packages,
    get_packages_from_requirements,
)
from .pypi_utils import get_pypi_package_info
from .version_utils import compare_versions


class CheckUpdatesCommand:
    """Command for checking package updates from PyPI."""

    def execute(
        self, requirements_file: str, show_all: bool, json_output: bool, timeout: int
    ):
        """Execute the check-updates command."""
        # Determine which packages to check
        if requirements_file:
            if not Path(requirements_file).exists():
                typer.secho(
                    f"Requirements file not found: {requirements_file}",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(code=1)
            packages_to_check = get_packages_from_requirements(requirements_file)
        else:
            packages_to_check = get_installed_packages()

        if not packages_to_check:
            typer.secho("No packages found to check.", fg=typer.colors.YELLOW)
            return

        # Check each package
        results = self._check_packages(packages_to_check, timeout, json_output)

        # Output results
        if json_output:
            typer.echo(json.dumps(results, indent=2))
        else:
            self._display_results(results, show_all)

    def _check_packages(
        self, packages: Dict[str, str], timeout: int, json_output: bool
    ) -> List[Dict[str, Any]]:
        """Check packages against PyPI and return results."""
        results: List[Dict[str, Any]] = []
        total_packages = len(packages)

        if not json_output:
            typer.secho(
                f"Checking {total_packages} packages for updates...",
                fg=typer.colors.BLUE,
            )

        for i, (package_name, current_version) in enumerate(packages.items(), 1):
            if not json_output:
                typer.echo(
                    f"Checking {package_name} ({i}/{total_packages})...", nl=False
                )

            pypi_info = get_pypi_package_info(package_name, timeout)

            if pypi_info:
                latest_version = pypi_info["info"]["version"]
                status = compare_versions(current_version, latest_version)

                result: Dict[str, Any] = {
                    "package": package_name,
                    "current": current_version,
                    "latest": latest_version,
                    "status": status,
                }

                if not json_output:
                    self._print_status(status, latest_version)
            else:
                result = {
                    "package": package_name,
                    "current": current_version,
                    "latest": "unknown",
                    "status": "error",
                }

                if not json_output:
                    typer.secho(" ✗ error", fg=typer.colors.RED)

            results.append(result)

        return results

    def _print_status(self, status: str, latest_version: str):
        """Print status indicator for a package."""
        if status == "outdated":
            typer.secho(f" ⬆ {latest_version}", fg=typer.colors.YELLOW)
        elif status == "current":
            typer.secho(" ✓ up to date", fg=typer.colors.GREEN)
        else:
            typer.secho(f" ? {status}", fg=typer.colors.CYAN)

    def _display_results(self, results: List[Dict[str, Any]], show_all: bool):
        """Display results summary and outdated packages."""
        outdated = [r for r in results if r["status"] == "outdated"]
        current = [r for r in results if r["status"] == "current"]
        errors = [r for r in results if r["status"] == "error"]

        typer.echo()
        typer.secho("Summary:", fg=typer.colors.BLUE, bold=True)
        typer.secho(f"  ✓ Up to date: {len(current)}", fg=typer.colors.GREEN)
        typer.secho(f"  ⬆ Outdated: {len(outdated)}", fg=typer.colors.YELLOW)
        typer.secho(f"  ✗ Errors: {len(errors)}", fg=typer.colors.RED)

        if outdated and not show_all:
            typer.echo()
            typer.secho("Outdated packages:", fg=typer.colors.YELLOW, bold=True)
            for result in outdated:
                typer.echo(
                    f"  {result['package']}: {result['current']} → {result['latest']}"
                )

            typer.echo()
            typer.secho("Update commands:", fg=typer.colors.CYAN)
            typer.echo("  ginx sync-versions --target latest    # Update all to latest")

            # Generate pip install command
            outdated_specs = [f"{r['package']}=={r['latest']}" for r in outdated]
            if len(outdated_specs) <= 5:
                typer.echo(f"  pip install --upgrade {' '.join(outdated_specs)}")
            else:
                typer.echo(
                    f"  pip install --upgrade {' '.join(outdated_specs[:3])} ..."
                )


class SyncVersionsCommand:
    """Command for syncing package versions."""

    def execute(self, target: str, requirements_file: str, dry_run: bool, yes: bool):
        """Execute the sync-versions command."""
        typer.secho("Version sync functionality coming soon!", fg=typer.colors.YELLOW)
        typer.echo("This will allow syncing packages to:")
        typer.echo("  - Latest versions from PyPI")
        typer.echo("  - Versions specified in requirements file")
        typer.echo("  - Specific version constraints")

        # TODO: Implement actual sync functionality
        # This would involve:
        # 1. Determining target versions
        # 2. Building pip install commands
        # 3. Executing updates with confirmation
        # 4. Handling conflicts and dependencies


class VersionDiffCommand:
    """Command for comparing versions between files."""

    def execute(self, file1: str, file2: str, show_all: bool):
        """Execute the version-diff command."""
        if not Path(file1).exists():
            typer.secho(f"File not found: {file1}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        if not Path(file2).exists():
            typer.secho(f"File not found: {file2}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        # Parse both files
        packages1 = get_packages_from_requirements(file1)
        packages2 = get_packages_from_requirements(file2)

        # Compare packages
        comparison = compare_package_sets(packages1, packages2)

        # Display results
        self._display_comparison(file1, file2, comparison, show_all)

    def _display_comparison(
        self,
        file1: str,
        file2: str,
        comparison: Dict[str, Dict[str, str]],
        show_all: bool,
    ):
        """Display comparison results."""
        typer.secho(
            f"Comparing {Path(file1).name} vs {Path(file2).name}:",
            fg=typer.colors.BLUE,
            bold=True,
        )
        typer.echo()

        different = comparison["different"]
        same = comparison["same"]
        only_first = comparison["only_in_first"]
        only_second = comparison["only_in_second"]

        if different:
            typer.secho("Different versions:", fg=typer.colors.YELLOW, bold=True)
            for package, versions in different.items():
                typer.echo(f"  {package}:")
                typer.echo(f"    {Path(file1).name}: {versions[0]}")
                typer.echo(f"    {Path(file2).name}: {versions[1]}")

        if only_first:
            typer.echo()
            typer.secho(f"Only in {Path(file1).name}:", fg=typer.colors.CYAN, bold=True)
            for package, version in only_first.items():
                typer.echo(f"  {package}: {version}")

        if only_second:
            typer.echo()
            typer.secho(f"Only in {Path(file2).name}:", fg=typer.colors.CYAN, bold=True)
            for package, version in only_second.items():
                typer.echo(f"  {package}: {version}")

        if show_all and same:
            typer.echo()
            typer.secho("Same versions:", fg=typer.colors.GREEN, bold=True)
            for package, version in same.items():
                typer.echo(f"  {package}: {version}")

        typer.echo()
        total_differences = len(different) + len(only_first) + len(only_second)
        typer.secho(
            f"Summary: {total_differences} differences, {len(same)} same",
            fg=typer.colors.BLUE,
        )


class PinVersionsCommand:
    """Command for pinning package versions."""

    def execute(self, requirements_file: str, output_file: str, force: bool):
        """Execute the pin-versions command."""
        # Get installed packages
        installed = get_installed_packages()

        if not installed:
            typer.secho("No installed packages found.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        # Filter out system packages
        installed = filter_system_packages(installed, exclude_system=True)

        # Determine output file
        if not output_file:
            if requirements_file:
                output_file = f"pinned-{Path(requirements_file).name}"
            else:
                output_file = "requirements-pinned.txt"

        if Path(output_file).exists() and not force:
            typer.secho(
                f"Output file '{output_file}' already exists. Use --force to overwrite.",
                fg=typer.colors.YELLOW,
            )
            raise typer.Exit(code=1)

        # Create pinned requirements
        header_comment = "Pinned package versions generated from current environment"
        pinned_lines = create_pinned_requirements(installed, header_comment)

        # Write to file
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(pinned_lines) + "\n")

            typer.secho(
                f"✓ Pinned {len(installed)} packages to {output_file}",
                fg=typer.colors.GREEN,
            )
            typer.echo(f"Install with: pip install -r {output_file}")

        except Exception as e:
            typer.secho(f"Error writing to {output_file}: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
