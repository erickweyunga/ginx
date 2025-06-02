from typing import Set

# Built-in command names that cannot be overridden by scripts
RESERVED_COMMANDS: Set[str] = {
    "version",
    "list",
    "run",
    "init",
    "validate",
    "deps",
    "graph",
    "debug-plugins",
}
