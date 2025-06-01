"""
Command registry for built-in commands.
"""

from typing import List

from ginx.cmd import RESERVED_COMMANDS


def is_command_reserved(command_name: str) -> bool:
    """Check if a command name is reserved."""
    return command_name in RESERVED_COMMANDS


def get_reserved_commands() -> List[str]:
    """Get list of reserved command names."""
    return list(RESERVED_COMMANDS)
