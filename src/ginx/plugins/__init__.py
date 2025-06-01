"""
Plugin system for Ginx.

This module provides the foundation for extending Ginx with custom plugins.
Plugins can add new commands, script processors, or other functionality.
"""

import importlib
import importlib.util
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer


class GinxPlugin(ABC):
    """Base class for Ginx plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass

    @property
    def description(self) -> str:
        """Plugin description."""
        return "No description provided"

    def initialize(self) -> None:
        """Initialize the plugin. Called when the plugin is loaded."""
        pass

    def add_commands(self, app: typer.Typer) -> None:
        """Add custom commands to the CLI app."""
        pass

    def process_script(
        self, script_name: str, script_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a script configuration before execution.

        Args:
            script_name: Name of the script
            script_config: Script configuration dictionary

        Returns:
            Modified script configuration
        """
        return script_config

    def pre_execution_hook(self, script_name: str, command: List[str]) -> List[str]:
        """
        Hook called before script execution.

        Args:
            script_name: Name of the script being executed
            command: Command list that will be executed

        Returns:
            Modified command list
        """
        return command

    def post_execution_hook(
        self, script_name: str, exit_code: int, duration: float
    ) -> None:
        """
        Hook called after script execution.

        Args:
            script_name: Name of the script that was executed
            exit_code: Exit code of the executed command
            duration: Execution duration in seconds
        """
        pass


class PluginManager:
    """Manages Ginx plugins."""

    def __init__(self) -> None:
        self._plugins: Dict[str, GinxPlugin] = {}
        self._initialized = False

    def discover_plugins(self, plugin_dirs: Optional[List[str]] = None) -> None:
        """
        Discover and load plugins from specified directories.

        Args:
            plugin_dirs: List of directories to search for plugins.
                        If None, uses default locations.
        """
        if plugin_dirs is None:
            plugin_dirs = self._get_default_plugin_dirs()

        for plugin_dir in plugin_dirs:
            if os.path.exists(plugin_dir):
                self._load_plugins_from_directory(plugin_dir)

    def _get_default_plugin_dirs(self) -> List[str]:
        """Get default plugin directories."""
        dirs: List[str] = []

        # Current directory plugins
        dirs.append(os.path.join(os.getcwd(), "ginx_plugins"))

        # User plugins directory
        home_dir = os.path.expanduser("~")
        dirs.append(os.path.join(home_dir, ".ginx", "plugins"))

        # System plugins directory
        if sys.platform.startswith("win"):
            dirs.append(
                os.path.join(os.environ.get("PROGRAMDATA", ""), "ginx", "plugins")
            )
        else:
            dirs.append("/usr/local/share/ginx/plugins")
            dirs.append("/opt/ginx/plugins")

        return dirs

    def _load_plugins_from_directory(self, plugin_dir: str) -> None:
        """Load plugins from a specific directory."""
        plugin_path = Path(plugin_dir)

        if not plugin_path.exists() or not plugin_path.is_dir():
            return

        # Look for Python files in the plugin directory
        for plugin_file in plugin_path.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue  # Skip private files

            try:
                self._load_plugin_from_file(plugin_file)
            except Exception as e:
                typer.secho(
                    f"Warning: Failed to load plugin {plugin_file.name}: {e}",
                    fg=typer.colors.YELLOW,
                )

    def _load_plugin_from_file(self, plugin_file: Path) -> None:
        """Load a plugin from a Python file."""
        module_name = f"ginx_plugin_{plugin_file.stem}"

        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {plugin_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Look for plugin classes
        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            if (
                isinstance(attr, type)
                and issubclass(attr, GinxPlugin)
                and attr != GinxPlugin
            ):

                try:
                    plugin_instance = attr()
                    self.register_plugin(plugin_instance)
                except Exception as e:
                    typer.secho(
                        f"Warning: Failed to instantiate plugin {attr_name}: {e}",
                        fg=typer.colors.YELLOW,
                    )

    def register_plugin(self, plugin: GinxPlugin) -> None:
        """Register a plugin instance."""
        if plugin.name in self._plugins:
            typer.secho(
                f"Warning: Plugin '{plugin.name}' is already registered",
                fg=typer.colors.YELLOW,
            )
            return

        self._plugins[plugin.name] = plugin

        try:
            plugin.initialize()
        except Exception as e:
            typer.secho(
                f"Warning: Plugin '{plugin.name}' initialization failed: {e}",
                fg=typer.colors.YELLOW,
            )

    def get_plugin(self, name: str) -> Optional[GinxPlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> Dict[str, GinxPlugin]:
        """Get all registered plugins."""
        return self._plugins.copy()

    def add_plugin_commands(self, app: typer.Typer) -> None:
        """Add commands from all plugins to the CLI app."""
        for plugin in self._plugins.values():
            try:
                plugin.add_commands(app)
            except Exception as e:
                typer.secho(
                    f"Warning: Plugin '{plugin.name}' failed to add commands: {e}",
                    fg=typer.colors.YELLOW,
                )

    def process_script(
        self, script_name: str, script_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process script configuration through all plugins."""
        for plugin in self._plugins.values():
            try:
                script_config = plugin.process_script(script_name, script_config)
            except Exception as e:
                typer.secho(
                    f"Warning: Plugin '{plugin.name}' script processing failed: {e}",
                    fg=typer.colors.YELLOW,
                )

        return script_config

    def run_pre_execution_hooks(
        self, script_name: str, command: List[str]
    ) -> List[str]:
        """Run pre-execution hooks from all plugins."""
        for plugin in self._plugins.values():
            try:
                command = plugin.pre_execution_hook(script_name, command)
            except Exception as e:
                typer.secho(
                    f"Warning: Plugin '{plugin.name}' pre-execution hook failed: {e}",
                    fg=typer.colors.YELLOW,
                )

        return command

    def run_post_execution_hooks(
        self, script_name: str, exit_code: int, duration: float
    ) -> None:
        """Run post-execution hooks from all plugins."""
        for plugin in self._plugins.values():
            try:
                plugin.post_execution_hook(script_name, exit_code, duration)
            except Exception as e:
                typer.secho(
                    f"Warning: Plugin '{plugin.name}' post-execution hook failed: {e}",
                    fg=typer.colors.YELLOW,
                )


# Global plugin manager instance
plugin_manager = PluginManager()


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance."""
    return plugin_manager


def auto_register_builtin_plugins() -> None:
    """Auto-register all discovered built-in plugins."""
    for plugin_name, plugin_class in _builtin_plugins.items():
        try:
            plugin_instance = plugin_class()
            plugin_manager.register_plugin(plugin_instance)
        except Exception as e:
            typer.secho(
                f"Warning: Failed to auto-register plugin {plugin_name}: {e}",
                fg=typer.colors.YELLOW,
            )


def _discover_builtin_plugins() -> Dict[str, Any]:
    """Discover and import built-in plugins from this directory."""
    plugins: Dict[Any, Any] = {}
    current_dir = Path(__file__).parent

    for item in current_dir.iterdir():
        if (
            item.is_dir()
            and not item.name.startswith("_")
            and item.name != "__pycache__"
        ):
            try:
                module = importlib.import_module(f".{item.name}", package=__name__)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, GinxPlugin)
                        and attr != GinxPlugin
                    ):
                        plugins[attr_name] = attr

            except ImportError:
                pass
            except Exception as e:
                typer.secho(
                    f"Warning: Failed to load built-in plugin {item.name}: {e}",
                    fg=typer.colors.YELLOW,
                )

    return plugins


# Auto-discover built-in plugins
_builtin_plugins = _discover_builtin_plugins()


__all__ = [
    "GinxPlugin",
    "PluginManager",
    "plugin_manager",
    "get_plugin_manager",
] + list(
    _builtin_plugins.keys()
)  # type: ignore


globals().update(_builtin_plugins)
