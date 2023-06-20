from __future__ import annotations

import inspect
import os
from importlib import import_module
from importlib.util import find_spec
from typing import Dict, TYPE_CHECKING, List

from serum import Context
from textual import log

from abacura.plugins import Plugin

if TYPE_CHECKING:
    pass


class PluginLoader:
    """Loads all plugins and registers them"""

    def __init__(self):
        super().__init__()
        self.plugins: Dict[str, Plugin] = {}

    def load_plugins(self, modules: List, plugin_context: Context) -> None:
        """Load plugins"""

        plugin_modules = []

        for mod in modules:
            log.info(f"Loading plugins from {mod}")
            spec = find_spec(mod)
            if not spec:
                continue

            for pathspec in spec.submodule_search_locations:
                for dirpath, _, filenames in os.walk(pathspec):
                    for filename in [f for f in filenames if f.endswith(".py") and not f.startswith('_') and os.path.join(dirpath, f) != __file__]:
                        shortpath = dirpath.replace(pathspec, "") or "/"
                        plugin_modules.append(mod + os.path.join(shortpath, filename))

        # import each one of the modules corresponding to each plugin .py file
        for pf in plugin_modules:
            package = pf.replace(os.sep, ".")[:-3]  # strip .py

            try:
                module = import_module(package)
            except Exception as exc:
                # TODO: Fix this hack to grab the session, maybe track the failed loads and return a list of failures
                session = plugin_context['session']
                session.show_exception(f"[bold red]# ERROR LOADING PLUGIN {package} (from {pf}): {repr(exc)}", exc)
                continue

            # Look for plugins subclasses within the module we just loaded and create a PluginHandler for each
            for name, c in inspect.getmembers(module, inspect.isclass):
                if c.__module__ == module.__name__ and inspect.isclass(c) and issubclass(c, Plugin):
                    with plugin_context:
                        plugin_instance: Plugin = c()

                    plugin_name = plugin_instance.get_name()
                    log(f"Adding plugin {name}.{plugin_name}")

                    self.plugins[plugin_name] = plugin_instance

                    # Look for listeners in the plugin
                    for member_name, member in inspect.getmembers(plugin_instance, callable):
                        if hasattr(member, 'event_name'):
                            log(f"Appending listener function '{member_name}'")
                            # TODO: Move this into the director
                            plugin_context['session'].event_manager.listener(member)
