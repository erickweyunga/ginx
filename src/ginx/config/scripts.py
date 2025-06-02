"""
Script configuration loading and validation.
"""

from typing import Any, Dict, List, Optional, Set, cast

import typer

from ginx.cmd import RESERVED_COMMANDS

from .loader import load_config


def is_script_name_reserved(script_name: str) -> bool:
    """
    Check if a script name conflicts with reserved commands.

    Args:
        script_name: Name of the script to check

    Returns:
        True if script name is reserved, False otherwise
    """
    return script_name in RESERVED_COMMANDS


def load_scripts(
    config: Optional[Dict[str, Any]] = None, show_warnings: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    Load and validate script configurations, excluding reserved names.

    Args:
        config: Pre-loaded configuration (loads if None)
        show_warnings: Whether to show warnings for skipped scripts

    Returns:
        Dictionary of validated script configurations
    """
    if config is None:
        config = load_config()

    scripts = config.get("scripts", {})

    if not scripts:
        return {}

    validated_scripts: Dict[str, Dict[str, Any]] = {}

    for name, script in scripts.items():
        if is_script_name_reserved(name):
            if show_warnings:
                typer.secho(
                    f"Warning: Script '{name}' conflicts with built-in command. Skipping.",
                    fg=typer.colors.YELLOW,
                )
            continue

        validated_script = validate_script_config(name, script)
        if validated_script:
            validated_scripts[name] = validated_script

    return validated_scripts


def validate_script_config(name: str, script: Any) -> Optional[Dict[str, Any]]:
    """
    Validate and normalize a single script configuration with dependency support.

    Args:
        name: Script name
        script: Script configuration (string or dict)

    Returns:
        Validated script configuration or None if invalid
    """
    if isinstance(script, str):
        # Simple string format - convert to dict
        return {
            "command": script,
            "description": f"Run: {script}",
            "depends": [],  # No dependencies for string format
        }

    elif isinstance(script, dict):
        # Dictionary format - validate required fields
        script_dict: Dict[str, Any] = cast(Dict[str, Any], script)

        if "command" not in script_dict:
            typer.secho(
                f"Script '{name}' missing required 'command' field",
                fg=typer.colors.RED,
            )
            return None

        # Ensure description exists
        if "description" not in script_dict:
            script_dict["description"] = f"Run {name} script"

        depends: List[str] = script_dict.get("depends", [])
        if isinstance(depends, str):
            script_dict["depends"] = [depends]
        else:
            script_dict["depends"] = [str(dep) for dep in depends]

        return script_dict

    else:
        typer.secho(
            f"Invalid script format for '{name}'. Expected string or dict.",
            fg=typer.colors.RED,
        )
        return None


def validate_dependencies(scripts: Dict[str, Dict[str, Any]]) -> List[str]:
    """
    Validate script dependencies and detect issues.

    Args:
        scripts: Dictionary of script configurations

    Returns:
        List of validation errors
    """
    errors: List[str] = []

    for script_name, script_config in scripts.items():
        depends = script_config.get("depends", [])

        for dep in depends:
            # Check if dependency exists
            if dep not in scripts:
                errors.append(
                    f"Script '{script_name}' depends on non-existent script '{dep}'"
                )

            # Check for self-dependency
            if dep == script_name:
                errors.append(f"Script '{script_name}' cannot depend on itself")

    # Check for circular dependencies
    cycles = detect_dependency_cycles(scripts)
    for cycle in cycles:
        cycle_str = " -> ".join(cycle + [cycle[0]])
        errors.append(f"Circular dependency detected: {cycle_str}")

    return errors


def detect_dependency_cycles(scripts: Dict[str, Dict[str, Any]]) -> List[List[str]]:
    """
    Detect circular dependencies using DFS.

    Args:
        scripts: Dictionary of script configurations

    Returns:
        List of dependency cycles (each cycle is a list of script names)
    """

    def dfs(
        node: str, path: List[str], visited: Set[str], rec_stack: Set[str]
    ) -> List[List[str]]:
        if node in rec_stack:
            cycle_start = path.index(node)
            return [path[cycle_start:]]

        if node in visited:
            return []

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        cycles: List[List[str]] = []
        depends = scripts.get(node, {}).get("depends", [])
        for dep in depends:
            if dep in scripts:
                cycles.extend(dfs(dep, path.copy(), visited, rec_stack.copy()))

        return cycles

    visited: Set[str] = set()
    all_cycles: List[List[str]] = []

    for script_name in scripts:
        if script_name not in visited:
            cycles = dfs(script_name, [], set(), set())
            all_cycles.extend(cycles)

    return all_cycles


def resolve_execution_order(
    scripts: Dict[str, Dict[str, Any]], target_script: str
) -> List[str]:
    """
    Resolve execution order for a script and its dependencies using topological sort.

    Args:
        scripts: Dictionary of script configurations
        target_script: Name of the script to execute

    Returns:
        List of script names in execution order (dependencies first)
    """
    if target_script not in scripts:
        return []

    def get_all_dependencies(script_name: str, collected: Set[str]) -> Set[str]:
        """Recursively collect all dependencies."""
        if script_name in collected or script_name not in scripts:
            return collected

        collected.add(script_name)
        depends = scripts[script_name].get("depends", [])

        for dep in depends:
            get_all_dependencies(dep, collected)

        return collected

    all_scripts = get_all_dependencies(target_script, set())

    def topological_sort(script_names: Set[str]) -> List[str]:
        in_degree = {name: 0 for name in script_names}

        for script_name in script_names:
            depends = scripts[script_name].get("depends", [])
            for dep in depends:
                if dep in script_names:
                    in_degree[script_name] += 1

        queue = [name for name, degree in in_degree.items() if degree == 0]
        result: List[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for script_name in script_names:
                depends = scripts[script_name].get("depends", [])
                if current in depends:
                    in_degree[script_name] -= 1
                    if in_degree[script_name] == 0:
                        queue.append(script_name)

        return result

    return topological_sort(all_scripts)


def get_script_variables(script_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract variable definitions from script configuration.

    Args:
        script_config: Script configuration dictionary

    Returns:
        Dictionary of variable definitions
    """
    return script_config.get("variables", {})


def has_variables(script_config: Dict[str, Any]) -> bool:
    """
    Check if script has variable definitions.

    Args:
        script_config: Script configuration dictionary

    Returns:
        True if script has variables defined
    """
    command = script_config.get("command", "")
    variables = script_config.get("variables", {})

    # Check for variable syntax in command
    has_new_syntax = "${" in command
    has_legacy_syntax = "EXTRA_" in command
    has_variable_definitions = bool(variables)

    return has_new_syntax or has_legacy_syntax or has_variable_definitions


def get_reserved_commands() -> Set[str]:
    """
    Get the set of reserved command names.

    Returns:
        Set of reserved command names
    """
    return RESERVED_COMMANDS.copy()


def add_reserved_command(command_name: str) -> None:
    """
    Add a command name to the reserved list (for plugins).

    Args:
        command_name: Command name to reserve
    """
    RESERVED_COMMANDS.add(command_name)


def list_conflicting_scripts(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get list of scripts that conflict with reserved commands.

    Args:
        config: Pre-loaded configuration (loads if None)

    Returns:
        Dictionary of conflicting script names and their configs
    """
    if config is None:
        config = load_config()

    scripts = config.get("scripts", {})
    conflicts: Dict[str, Any] = {}

    for name, script in scripts.items():
        if is_script_name_reserved(name):
            conflicts[name] = script

    return conflicts
