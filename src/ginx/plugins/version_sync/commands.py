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
    ) -> None:
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

    def _print_status(self, status: str, latest_version: str) -> None:
        """Print status indicator for a package."""
        if status == "outdated":
            typer.secho(f" ⬆ {latest_version}", fg=typer.colors.YELLOW)
        elif status == "current":
            typer.secho(" ✓ up to date", fg=typer.colors.GREEN)
        else:
            typer.secho(f" ? {status}", fg=typer.colors.CYAN)

    def _display_results(self, results: List[Dict[str, Any]], show_all: bool) -> None:
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

    def execute(self, target: str, requirements_file: str, dry_run: bool, yes: bool) -> None:
        """Command for syncing package versions."""

        # Get current installed packages
        current_packages = get_installed_packages()
        if not current_packages:
            typer.secho("No installed packages found.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        # Determine target versions based on sync target
        target_packages = self._determine_target_versions(
            target, requirements_file, current_packages
        )

        if not target_packages:
            typer.secho("No target packages to sync to.", fg=typer.colors.YELLOW)
            return

        # Find packages that need updating
        updates_needed = self._find_updates_needed(current_packages, target_packages)

        if not updates_needed:
            typer.secho(
                "✓ All packages are already at target versions.", fg=typer.colors.GREEN
            )
            return

        # Display what will be updated
        self._display_planned_updates(updates_needed, dry_run)

        if dry_run:
            typer.secho(
                "Dry run complete. No packages were updated.", fg=typer.colors.BLUE
            )
            return

        # Confirm with user unless --yes flag is used
        if not yes and not self._confirm_updates(updates_needed):
            typer.secho("Update cancelled.", fg=typer.colors.YELLOW)
            return

        # Execute the updates
        self._execute_updates(updates_needed)

    def _determine_target_versions(
        self, target: str, requirements_file: str, current_packages: Dict[str, str]
    ) -> Dict[str, str]:
        """Determine target versions based on sync target."""

        if target == "latest":
            return self._get_latest_versions(current_packages)
        elif target == "requirements" or requirements_file:
            return self._get_requirements_versions(
                requirements_file or "requirements.txt"
            )
        elif (
            target.startswith(">=")
            or target.startswith("==")
            or target.startswith("~=")
        ):
            # Handle version constraint targets like ">=2.0.0"
            return self._apply_version_constraint(current_packages, target)
        elif Path(target).exists():
            # Target is a requirements file path
            return self._get_requirements_versions(target)
        else:
            typer.secho(f"Unknown target: {target}", fg=typer.colors.RED)
            typer.echo("Valid targets:")
            typer.echo("  latest              - Update to latest PyPI versions")
            typer.echo("  requirements        - Sync to requirements.txt")
            typer.echo("  /path/to/file.txt   - Sync to specific requirements file")
            typer.echo("  >=1.0.0             - Apply version constraint")
            raise typer.Exit(code=1)

    def _get_latest_versions(self, current_packages: Dict[str, str]) -> Dict[str, str]:
        """Get latest versions from PyPI for all packages."""
        target_packages: Dict[str, Any] = {}
        total_packages = len(current_packages)

        typer.secho(
            f"Fetching latest versions for {total_packages} packages...",
            fg=typer.colors.BLUE,
        )

        for i, package_name in enumerate(current_packages.keys(), 1):
            typer.echo(f"Checking {package_name} ({i}/{total_packages})...", nl=False)

            pypi_info = get_pypi_package_info(package_name, timeout=30)
            if pypi_info:
                latest_version = pypi_info["info"]["version"]
                target_packages[package_name] = latest_version
                typer.secho(f" {latest_version}", fg=typer.colors.GREEN)
            else:
                typer.secho(" ✗ failed", fg=typer.colors.RED)
                # Keep current version if PyPI lookup fails
                target_packages[package_name] = current_packages[package_name]

        return target_packages

    def _get_requirements_versions(self, requirements_file: str) -> Dict[str, str]:
        """Get versions from requirements file."""
        if not Path(requirements_file).exists():
            typer.secho(
                f"Requirements file not found: {requirements_file}", fg=typer.colors.RED
            )
            raise typer.Exit(code=1)

        typer.secho(
            f"Reading target versions from {requirements_file}...", fg=typer.colors.BLUE
        )
        return get_packages_from_requirements(requirements_file)

    def _apply_version_constraint(
        self, current_packages: Dict[str, str], constraint: str
    ) -> Dict[str, str]:
        """Apply a version constraint to all packages."""
        typer.secho(
            f"Applying constraint {constraint} to all packages...", fg=typer.colors.BLUE
        )

        # For now, this is a simplified implementation
        # In practice, you'd want to use packaging.specifiers for proper constraint handling
        target_packages: Dict[str, Any] = {}

        for package_name in current_packages.keys():
            # This is a simplified example - you'd want more sophisticated constraint handling
            if constraint.startswith(">="):
                # min_version = constraint[2:]
                pypi_info = get_pypi_package_info(package_name, timeout=30)
                if pypi_info:
                    latest = pypi_info["info"]["version"]
                    # Use latest if it satisfies constraint, otherwise keep current
                    target_packages[package_name] = latest
                else:
                    target_packages[package_name] = current_packages[package_name]
            else:
                target_packages[package_name] = current_packages[package_name]

        return target_packages

    def _find_updates_needed(
        self, current_packages: Dict[str, str], target_packages: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """Find packages that need updating."""
        updates_needed: List[Dict[str, Any]] = []

        for package_name in current_packages.keys():
            current_version = current_packages[package_name]
            target_version = target_packages.get(package_name)

            if target_version and current_version != target_version:
                status = compare_versions(current_version, target_version)
                updates_needed.append(
                    {
                        "package": package_name,
                        "current": current_version,
                        "target": target_version,
                        "status": status,
                    }
                )

        return updates_needed

    def _display_planned_updates(
        self, updates_needed: List[Dict[str, str]], dry_run: bool
    ) -> None:
        """Display what packages will be updated."""
        typer.echo()
        action = "Would update" if dry_run else "Will update"
        typer.secho(
            f"{action} {len(updates_needed)} packages:", fg=typer.colors.BLUE, bold=True
        )

        for update in updates_needed:
            package = update["package"]
            current = update["current"]
            target = update["target"]
            status = update["status"]

            if status == "outdated":
                color = typer.colors.GREEN
                symbol = "⬆"
            elif status == "current":
                continue  # Skip if somehow current
            else:
                color = typer.colors.YELLOW
                symbol = "→"

            typer.secho(f"  {symbol} {package}: {current} → {target}", fg=color)

    def _confirm_updates(self, updates_needed: List[Dict[str, str]]) -> bool:
        """Ask user to confirm updates."""
        typer.echo()
        return typer.confirm(f"Proceed with updating {len(updates_needed)} packages?")

    def _execute_updates(self, updates_needed: List[Dict[str, str]]) -> None:
        """Execute the package updates."""
        import subprocess
        import sys

        typer.echo()
        typer.secho("Executing updates...", fg=typer.colors.BLUE, bold=True)

        # Group updates into batches to avoid command line length limits
        batch_size = 10
        batches = [
            updates_needed[i : i + batch_size]
            for i in range(0, len(updates_needed), batch_size)
        ]

        success_count = 0
        failed_packages: List[str] = []

        for batch_num, batch in enumerate(batches, 1):
            if len(batches) > 1:
                typer.echo(f"Batch {batch_num}/{len(batches)}:")

            # Build pip install command
            package_specs = [
                f"{update['package']}=={update['target']}" for update in batch
            ]
            cmd = [sys.executable, "-m", "pip", "install"] + package_specs

            try:
                # Execute pip install
                result = subprocess.run(
                    cmd, check=False, capture_output=True, text=True
                )

                if result.returncode == 0:
                    for update in batch:
                        typer.secho(
                            f"  ✓ {update['package']}: {update['current']} → {update['target']}",
                            fg=typer.colors.GREEN,
                        )
                        success_count += 1
                else:
                    # If batch fails, try individual packages
                    typer.secho(
                        f"  Batch failed, trying individual packages...",
                        fg=typer.colors.YELLOW,
                    )
                    for update in batch:
                        if self._install_single_package(update):
                            success_count += 1
                        else:
                            failed_packages.append(update["package"])

            except Exception as e:
                typer.secho(f"  Error executing batch: {e}", fg=typer.colors.RED)
                for update in batch:
                    failed_packages.append(update["package"])

        # Display final results
        typer.echo()
        typer.secho("Update Summary:", fg=typer.colors.BLUE, bold=True)
        typer.secho(f"  ✓ Successfully updated: {success_count}", fg=typer.colors.GREEN)

        if failed_packages:
            typer.secho(
                f"  ✗ Failed to update: {len(failed_packages)}", fg=typer.colors.RED
            )
            typer.echo("Failed packages:")
            for package in failed_packages:
                typer.echo(f"    - {package}")
            typer.echo()
            typer.echo(
                "You may need to update these packages manually or resolve conflicts."
            )

    def _install_single_package(self, update: Dict[str, str]) -> bool:
        """Install a single package and return success status."""
        import subprocess
        import sys

        package_spec = f"{update['package']}=={update['target']}"
        cmd = [sys.executable, "-m", "pip", "install", package_spec]

        try:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if result.returncode == 0:
                typer.secho(
                    f"  ✓ {update['package']}: {update['current']} → {update['target']}",
                    fg=typer.colors.GREEN,
                )
                return True
            else:
                typer.secho(
                    f"  ✗ {update['package']}: failed to update", fg=typer.colors.RED
                )
                return False
        except Exception:
            typer.secho(
                f"  ✗ {update['package']}: error during update", fg=typer.colors.RED
            )
            return False


class VersionDiffCommand:
    """Command for comparing versions between files."""

    def execute(self, file1: str, file2: str, show_all: bool) -> None:
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
    ) -> None:
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

    def execute(self, requirements_file: str, output_file: str, force: bool) -> None:
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
