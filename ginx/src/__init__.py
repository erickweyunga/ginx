"""
Ginx - A command-line script runner powered by YAML configuration.

This package provides a powerful way to define and run project scripts
using YAML configuration files.
"""

__version__ = "0.1.0"
__author__ = "Ginx Contributors"
__email__ = "maverickweyunga@gmail.com"
__description__ = "A command-line script runner powered by YAML configuration"

from .loader import create_sample_config, find_config_file, load_scripts
from .utils import (
    check_dependencies,
    detect_virtual_environment,
    expand_variables,
    extract_commands_from_shell_string,
    find_requirements_files,
    format_duration,
    get_project_root,
    parse_requirements_file,
    run_command_with_streaming,
    run_command_with_streaming_shell,
    suggest_virtual_environment,
    validate_command,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "load_scripts",
    "create_sample_config",
    "find_config_file",
    "parse_requirements_file",
    "find_requirements_files",
    "validate_command",
    "run_command_with_streaming",
    "detect_virtual_environment",
    "suggest_virtual_environment",
    "run_command_with_streaming_shell",
    "format_duration",
    "expand_variables",
    "check_dependencies",
    "extract_commands_from_shell_string",
    "get_project_root",
]
