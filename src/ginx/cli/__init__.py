"""
Ginx CLI module - Main application and command registration.
"""

from .app import app, initialize_app
from .registration import register_script_commands
from .commands import (
    version_command,
    list_scripts_command,
    validate_config_command,
    check_dependencies_command,
    debug_plugins_command,
    init_config_command,
    run_script_command,
)


# Register built-in commands
app.command("version", help="Show Ginx version.")(version_command)
app.command("list", help="List all available scripts.")(list_scripts_command)
app.command("validate", help="Validate the configuration file.")(validate_config_command)
app.command("deps", help="Check dependencies and requirements files.")(check_dependencies_command)
app.command("debug-plugins", help="Debug plugin loading status.")(debug_plugins_command)
app.command("init", help="Create a sample ginx.yaml configuration file.")(init_config_command)
app.command("run", help="Run a script by name.")(run_script_command)

# Register dynamic script commands
register_script_commands(app)

__all__ = [
    "app",
    "initialize_app",
    "register_script_commands",
]
