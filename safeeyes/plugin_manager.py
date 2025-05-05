#!/usr/bin/env python
# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2017  Gobinath

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""PluginManager loads all enabled plugins and call their lifecycle methods.

A plugin must have the following directory structure:
<plugin-id>
    |- config.json
    |- plugin.py
    |- icon.png (Optional)

The plugin.py can have following methods but all are optional:
 - description()
    If a custom description has to be displayed, use this function
 - init(context, safeeyes_config, plugin_config)
    Initialize the plugin. Will be called after loading and after every changes in
    configuration
 - on_start()
    Executes when Safe Eyes is enabled
 - on_stop()
    Executes when Safe Eyes is disabled
 - on_exit()
    Executes before Safe Eyes exits
 - on_pre_break(break_obj)
    Executes at the start of the prepare time for a break
 - on_start_break(break_obj)
    Executes when a break starts
 - on_stop_break()
    Executes when a break stops
 - on_countdown(countdown, seconds)
    Executes every second throughout a break
 - update_next_break(break_obj, break_time)
    Executes when the next break changes
 - enable()
    Executes once the plugin.py is loaded as a module
 - disable()
    Executes if the plugin is disabled at the runtime by the user
"""

import importlib
import logging
import os
import sys

from safeeyes import utility
from safeeyes.model import PluginDependency, RequiredPluginException

sys.path.append(os.path.abspath(utility.SYSTEM_PLUGINS_DIR))
sys.path.append(os.path.abspath(utility.USER_PLUGINS_DIR))

HORIZONTAL_LINE_LENGTH = 64


class PluginManager:
    """Imports the Safe Eyes plugins and calls the methods defined in those plugins."""

    def __init__(self):
        logging.info("Load all the plugins")
        self.__plugins = {}
        self.last_break = None
        self.horizontal_line = "─" * HORIZONTAL_LINE_LENGTH

    def init(self, context, config):
        """Initialize all the plugins with init(context, safe_eyes_config,
        plugin_config) function.
        """
        # Load the plugins
        for plugin in config.get("plugins"):
            try:
                loaded_plugin = LoadedPlugin(plugin)
                self.__plugins[loaded_plugin.id] = loaded_plugin
            except RequiredPluginException as e:
                raise e
            except BaseException as e:
                traceback_wanted = (
                    logging.getLogger().getEffectiveLevel() == logging.DEBUG
                )
                if traceback_wanted:
                    import traceback

                    traceback.print_exc()
                logging.error("Error in loading the plugin %s: %s", plugin["id"], e)
                continue
        # Initialize the plugins
        for plugin in self.__plugins.values():
            plugin.init_plugin(context, config)
        return True

    def needs_retry(self):
        return self.get_retryable_error() is not None

    def get_retryable_error(self):
        for plugin in self.__plugins.values():
            if plugin.required_plugin and plugin.errored and plugin.enabled:
                if (
                    isinstance(plugin.last_error, PluginDependency)
                    and plugin.last_error.retryable
                ):
                    return RequiredPluginException(
                        plugin.id, plugin.get_name(), plugin.last_error
                    )

        return None

    def retry_errored_plugins(self):
        for plugin in self.__plugins.values():
            if plugin.required_plugin and plugin.errored and plugin.enabled:
                if (
                    isinstance(plugin.last_error, PluginDependency)
                    and plugin.last_error.retryable
                ):
                    plugin.reload_errored()

    def start(self):
        """Execute the on_start() function of plugins."""
        for plugin in self.__plugins.values():
            plugin.call_plugin_method("on_start")
        return True

    def stop(self):
        """Execute the on_stop() function of plugins."""
        for plugin in self.__plugins.values():
            plugin.call_plugin_method("on_stop")
        return True

    def exit(self):
        """Execute the on_exit() function of plugins."""
        for plugin in self.__plugins.values():
            plugin.call_plugin_method("on_exit")
        return True

    def pre_break(self, break_obj):
        """Execute the on_pre_break(break_obj) function of plugins."""
        for plugin in self.__plugins.values():
            if plugin.call_plugin_method_break_obj("on_pre_break", 1, break_obj):
                return False
        return True

    def start_break(self, break_obj):
        """Execute the start_break(break_obj) function of plugins."""
        self.last_break = break_obj
        for plugin in self.__plugins.values():
            if plugin.call_plugin_method_break_obj("on_start_break", 1, break_obj):
                return False

        return True

    def stop_break(self):
        """Execute the stop_break() function of plugins."""
        for plugin in self.__plugins.values():
            plugin.call_plugin_method("on_stop_break")

    def countdown(self, countdown, seconds):
        """Execute the on_countdown(countdown, seconds) function of plugins."""
        for plugin in self.__plugins.values():
            plugin.call_plugin_method("on_countdown", 2, countdown, seconds)

    def update_next_break(self, break_obj, break_time):
        """Execute the update_next_break(break_time) function of plugins."""
        for plugin in self.__plugins.values():
            plugin.call_plugin_method_break_obj(
                "update_next_break", 2, break_obj, break_time
            )
        return True

    def get_break_screen_widgets(self, break_obj):
        """Return the HTML widget generated by the plugins.

        The widget is generated by calling the get_widget_title and
        get_widget_content functions of plugins.
        """
        widget = ""
        for plugin in self.__plugins.values():
            try:
                title = plugin.call_plugin_method_break_obj(
                    "get_widget_title", 1, break_obj
                )
                if title is None or not isinstance(title, str) or title == "":
                    continue
                content = plugin.call_plugin_method_break_obj(
                    "get_widget_content", 1, break_obj
                )
                if content is None or not isinstance(content, str) or content == "":
                    continue
                title = title.upper().strip()
                if title == "":
                    continue
                widget += "<b>{}</b>\n{}\n{}\n\n\n".format(
                    title, self.horizontal_line, content
                )
            except BaseException:
                continue
        return widget.strip()

    def get_break_screen_tray_actions(self, break_obj):
        """Return Tray Actions."""
        actions = []
        for plugin in self.__plugins.values():
            action = plugin.call_plugin_method_break_obj(
                "get_tray_action", 1, break_obj
            )
            if action:
                actions.append(action)

        return actions


class LoadedPlugin:
    # state of the plugin
    enabled: bool = False
    break_override_allowed: bool = False
    errored: bool = False
    required_plugin: bool = False

    # misc data
    # FIXME: rename to plugin_config to plugin_json? plugin_config and config are easy
    # to confuse
    config = None
    plugin_config = None
    plugin_dir = None
    module = None
    last_error = None
    id = None

    def __init__(self, plugin):
        (plugin_config, plugin_dir) = self._load_config_json(plugin["id"])

        self.id = plugin["id"]
        self.plugin_config = plugin_config
        self.plugin_dir = plugin_dir
        self.enabled = plugin["enabled"]
        self.break_override_allowed = plugin_config.get("break_override_allowed", False)
        self.required_plugin = plugin_config.get("required_plugin", False)

        self.config = dict(plugin.get("settings", {}))
        self.config["path"] = os.path.join(plugin_dir, plugin["id"])

        if self.enabled or self.break_override_allowed:
            plugin_path = os.path.join(plugin_dir, self.id)
            message = utility.check_plugin_dependencies(
                plugin["id"], plugin_config, plugin.get("settings", {}), plugin_path
            )

            if message:
                self.errored = True
                self.last_error = message
                if self.required_plugin and not (
                    isinstance(message, PluginDependency) and message.retryable
                ):
                    raise RequiredPluginException(
                        plugin["id"], plugin_config["meta"]["name"], message
                    )
                return

            self._import_plugin()

    def reload_config(self, plugin):
        if self.enabled and not plugin["enabled"]:
            self.enabled = False
            if not self.errored and utility.has_method(self.module, "disable"):
                self.module.disable()

        if not self.enabled and plugin["enabled"]:
            self.enabled = True

        # Update the config
        self.config = dict(plugin.get("settings", {}))
        self.config["path"] = os.path.join(self.plugin_dir, plugin["id"])

        if self.enabled or self.break_override_allowed:
            plugin_path = os.path.join(self.plugin_dir, self.id)
            message = utility.check_plugin_dependencies(
                self.id, self.plugin_config, self.config, plugin_path
            )

            if message:
                self.errored = True
                self.last_error = message
            elif self.errored:
                self.errored = False
                self.last_error = None

            if not self.errored and self.module is None:
                # No longer errored, import the module now
                self._import_plugin()

    def reload_errored(self):
        if not self.errored:
            return

        if self.enabled or self.break_override_allowed:
            plugin_path = os.path.join(self.plugin_dir, self.id)
            message = utility.check_plugin_dependencies(
                self.id, self.plugin_config, self.config, plugin_path
            )

            if message:
                self.errored = True
                self.last_error = message
            elif self.errored:
                self.errored = False
                self.last_error = None

            if not self.errored and self.module is None:
                # No longer errored, import the module now
                self._import_plugin()

    def get_name(self):
        return self.plugin_config["meta"]["name"]

    def _import_plugin(self):
        if self.errored:
            # do not try to import errored plugin
            return

        self.module = importlib.import_module((self.id + ".plugin"))
        logging.info("Successfully loaded %s", str(self.module))

        if utility.has_method(self.module, "enable"):
            self.module.enable()

    def _load_config_json(self, plugin_id):
        # Look for plugin.py
        if os.path.isfile(
            os.path.join(utility.SYSTEM_PLUGINS_DIR, plugin_id, "plugin.py")
        ):
            plugin_dir = utility.SYSTEM_PLUGINS_DIR
        elif os.path.isfile(
            os.path.join(utility.USER_PLUGINS_DIR, plugin_id, "plugin.py")
        ):
            plugin_dir = utility.USER_PLUGINS_DIR
        else:
            raise Exception("plugin.py not found for the plugin: %s", plugin_id)
        # Look for config.json
        plugin_path = os.path.join(plugin_dir, plugin_id)
        plugin_config_path = os.path.join(plugin_path, "config.json")
        if not os.path.isfile(plugin_config_path):
            raise Exception("config.json not found for the plugin: %s", plugin_id)
        plugin_config = utility.load_json(plugin_config_path)
        if plugin_config is None:
            raise Exception("config.json empty/invalid for the plugin: %s", plugin_id)

        return (plugin_config, plugin_dir)

    def init_plugin(self, context, safeeyes_config):
        if self.errored:
            return
        if self.break_override_allowed or self.enabled:
            if utility.has_method(self.module, "init", 3):
                self.module.init(context, safeeyes_config, self.config)

    def call_plugin_method_break_obj(
        self, method_name: str, num_args, break_obj, *args, **kwargs
    ):
        if self.errored:
            return None

        enabled = False
        if self.break_override_allowed:
            enabled = break_obj.plugin_enabled(self.id, self.enabled)
        else:
            enabled = self.enabled

        if enabled:
            return self._call_plugin_method_internal(
                method_name, num_args, break_obj, *args, **kwargs
            )

        return None

    def call_plugin_method(self, method_name: str, num_args=0, *args, **kwargs):
        if self.errored:
            return None

        if self.enabled:
            return self._call_plugin_method_internal(
                method_name, num_args, *args, **kwargs
            )

        return None

    def _call_plugin_method_internal(
        self, method_name: str, num_args=0, *args, **kwargs
    ):
        # FIXME: cache if method exists
        if utility.has_method(self.module, method_name, num_args):
            return getattr(self.module, method_name)(*args, **kwargs)
        return None
