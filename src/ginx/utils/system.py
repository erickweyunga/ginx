"""
System and environment-related utility functions.
"""

import os
import platform
from typing import Dict, Optional


def get_shell() -> str:
    """
    Get the current shell being used.

    Returns:
        Shell name (bash, zsh, fish, cmd, powershell, etc.)
    """
    if platform.system() == "Windows":
        return os.environ.get("COMSPEC", "cmd").split("\\")[-1].lower()
    else:
        shell = os.environ.get("SHELL", "/bin/bash")
        return shell.split("/")[-1]


def expand_variables(command: str, env_vars: Optional[Dict[str, str]] = None) -> str:
    """
    Expand environment variables in command string.

    Args:
        command: Command string that may contain environment variables
        env_vars: Additional environment variables to use for expansion

    Returns:
        Command string with expanded variables
    """
    if env_vars:
        # Create a copy of os.environ and update with additional vars
        expanded_env = os.environ.copy()
        expanded_env.update(env_vars)

        # Expand variables
        for key, value in expanded_env.items():
            command = command.replace(f"${key}", value)
            command = command.replace(f"${{{key}}}", value)
            if platform.system() == "Windows":
                command = command.replace(f"%{key}%", value)

    return os.path.expandvars(command)
