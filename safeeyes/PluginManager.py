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
"""
PluginManager loads all enabled plugins and call their lifecycle methods.
A plugin must have the following directory structure:
<plugin-id>
    |- config.json
    |- plugin.py
    |- icon.png (Optional)

The plugin.py can have following methods but all are optional:
 - description()
    If a custom description has to be displayed, use this function
 - on_init(context, safeeyes_config, plugin_config)
    Initialize the plugin. Will be called after loading and after every changes in configuration
 - on_start()
    Executes when Safe Eyes is enabled
 - on_stop()
    Executes when Safe Eyes is disabled
 - enable()
    Executes once the plugin.py is loaded as a module
 - disable()
    Executes if the plugin is disabled at the runtime by the user
 - on_exit()
    Executes before Safe Eyes exits
"""

import importlib
import inspect
import logging
import os
import sys

from safeeyes import Utility

sys.path.append(os.path.abspath(Utility.SYSTEM_PLUGINS_DIR))
sys.path.append(os.path.abspath(Utility.USER_PLUGINS_DIR))

HORIZONTAL_LINE_LENGTH = 64


class PluginManager(object):
    """
    Imports the Safe Eyes plugins and calls the methods defined in those plugins.
    """

    def __init__(self, context, config):
        logging.info('Load all the plugins')
        self.__plugins = {}
        self.__plugins_on_init = []
        self.__plugins_on_start = []
        self.__plugins_on_stop = []
        self.__plugins_on_exit = []
        self.__plugins_on_pre_break = []
        self.__plugins_on_start_break = []
        self.__plugins_on_stop_break = []
        self.__plugins_on_countdown = []
        self.__plugins_update_next_break = []
        self.__widget_plugins = []
        self.__tray_actions_plugins = []
        self.last_break = None
        self.horizontal_line = '─' * HORIZONTAL_LINE_LENGTH

    def init(self, context, config):
        """
        Initialize all the plugins with init(context, safeeyes_config, plugin_config) function.
        """
        # Load the plugins
        for plugin in config.get('plugins'):
            try:
                self.__load_plugin(plugin, context)
            except BaseException:
                logging.error('Error in loading the plugin: %s', plugin['id'])
                continue
        # Initialize the plugins
        for plugin in self.__plugins_on_init:
            plugin['module'].init(context, config, plugin['config'])
        return True

    def start(self):
        """
        Execute the on_start() function of plugins.
        """
        for plugin in self.__plugins_on_start:
            plugin['module'].on_start()
        return True

    def stop(self):
        """
        Execute the on_stop() function of plugins.
        """
        for plugin in self.__plugins_on_stop:
            plugin['module'].on_stop()
        return True

    def exit(self):
        """
        Execute the on_exit() function of plugins.
        """
        for plugin in self.__plugins_on_exit:
            plugin['module'].on_exit()
        return True

    def pre_break(self, break_obj):
        """
        Execute the on_pre_break(break_obj) function of plugins.
        """
        for plugin in self.__plugins_on_pre_break:
            if break_obj.plugin_enabled(plugin['id'], plugin['enabled']):
                if plugin['module'].on_pre_break(break_obj):
                    return False
        return True

    def start_break(self, break_obj):
        """
        Execute the start_break(break_obj) function of plugins.
        """
        self.last_break = break_obj
        for plugin in self.__plugins_on_start_break:
            if break_obj.plugin_enabled(plugin['id'], plugin['enabled']):
                if plugin['module'].on_start_break(break_obj):
                    return False

        return True

    def stop_break(self):
        """
        Execute the stop_break() function of plugins.
        """
        for plugin in self.__plugins_on_stop_break:
            if self.last_break.plugin_enabled(plugin['id'], plugin['enabled']):
                plugin['module'].on_stop_break()

    def countdown(self, countdown, seconds):
        """
        Execute the on_countdown(countdown, seconds) function of plugins.
        """
        for plugin in self.__plugins_on_countdown:
            if self.last_break.plugin_enabled(plugin['id'], plugin['enabled']):
                plugin['module'].on_countdown(countdown, seconds)

    def update_next_break(self, break_obj, break_time):
        """
        Execute the update_next_break(break_time) function of plugins.
        """
        for plugin in self.__plugins_update_next_break:
            plugin['module'].update_next_break(break_obj, break_time)
        return True

    def get_break_screen_widgets(self, break_obj):
        """
        Return the HTML widget generated by the plugins.
        The widget is generated by calling the get_widget_title and get_widget_content functions of plugins.
        """
        widget = ''
        for plugin in self.__widget_plugins:
            if break_obj.plugin_enabled(plugin['id'], plugin['enabled']):
                try:
                    title = plugin['module'].get_widget_title(break_obj).upper().strip()
                    if title == '':
                        continue
                    content = plugin['module'].get_widget_content(break_obj)
                    if content == '':
                        continue
                    widget += '<b>{}</b>\n{}\n{}\n\n\n'.format(title, self.horizontal_line, content)
                except BaseException:
                    continue
        return widget.strip()

    def get_break_screen_tray_actions(self, break_obj):
        """
        Return Tray Actions.
        """
        actions = []
        for plugin in self.__tray_actions_plugins:
            if break_obj.plugin_enabled(plugin['id'], plugin['enabled']):
                action = plugin['module'].get_tray_action(break_obj)
                if action:
                    actions.append(action)

        return actions

    def __has_method(self, module, method_name, no_of_args=0):
        """
        Check whether the given function is defined in the module or not.
        """
        if hasattr(module, method_name):
            if len(inspect.getargspec(getattr(module, method_name)).args) == no_of_args:
                return True
        return False

    def __remove_if_exists(self, list_of_items, item):
        """
        Remove the item from the list_of_items it it exists.
        """
        if item in list_of_items:
            list_of_items.remove(item)

    def __load_plugin(self, plugin, context):
        """
        Load the given plugin.
        """
        plugin_enabled = plugin['enabled']
        if plugin['id'] in self.__plugins and not plugin_enabled:
            # A disabled plugin but that was loaded earlier
            plugin_obj = self.__plugins[plugin['id']]
            if plugin_obj['enabled']:
                # Previously enabled but now disabled
                plugin_obj['enabled'] = False
                self.__remove_if_exists(self.__plugins_on_start, plugin_obj)
                self.__remove_if_exists(self.__plugins_on_stop, plugin_obj)
                self.__remove_if_exists(self.__plugins_on_exit, plugin_obj)
                self.__remove_if_exists(self.__plugins_update_next_break, plugin_obj)
                # Call the plugin.disable method if available
                if self.__has_method(plugin_obj['module'], 'disable'):
                    plugin_obj['module'].disable()
                logging.info("Successfully unloaded the plugin '%s'", plugin['id'])

            if not plugin_obj['break_override_allowed']:
                # Remaining methods also should be removed
                self.__remove_if_exists(self.__plugins_on_init, plugin_obj)
                self.__remove_if_exists(self.__plugins_on_pre_break, plugin_obj)
                self.__remove_if_exists(self.__plugins_on_start_break, plugin_obj)
                self.__remove_if_exists(self.__plugins_on_stop_break, plugin_obj)
                self.__remove_if_exists(self.__plugins_on_countdown, plugin_obj)
                self.__remove_if_exists(self.__widget_plugins, plugin_obj)
                self.__remove_if_exists(self.__tray_actions_plugins, plugin_obj)
                del self.__plugins[plugin['id']]
            return

        # Look for plugin.py
        plugin_dir = None
        if os.path.isfile(os.path.join(Utility.SYSTEM_PLUGINS_DIR, plugin['id'], 'plugin.py')):
            plugin_dir = Utility.SYSTEM_PLUGINS_DIR
        elif os.path.isfile(os.path.join(Utility.USER_PLUGINS_DIR, plugin['id'], 'plugin.py')):
            plugin_dir = Utility.USER_PLUGINS_DIR
        else:
            logging.error('plugin.py not found for the plugin: %s', plugin['id'])
            return
        # Look for config.json
        plugin_path = os.path.join(plugin_dir, plugin['id'])
        plugin_config_path = os.path.join(plugin_path, 'config.json')
        if not os.path.isfile(plugin_config_path):
            logging.error('config.json not found for the plugin: %s', plugin['id'])
            return
        plugin_config = Utility.load_json(plugin_config_path)
        if plugin_config is None:
            return

        if (plugin_enabled or plugin_config.get('break_override_allowed', False)):
            if plugin['id'] in self.__plugins:
                # The plugin is already enabled or partially loaded due to break_override_allowed
                # Use the existing plugin object
                plugin_obj = self.__plugins[plugin['id']]
                
                # Update the config
                plugin_obj['config'] = dict(plugin.get('settings', {}))
                plugin_obj['config']['path'] = os.path.join(plugin_dir, plugin['id'])

                if plugin_obj['enabled']:
                    # Already loaded completely
                    return
                # Plugin was partially loaded due to break_override_allowed
                if plugin_enabled:
                    # Load the rest of the methods
                    plugin_obj['enabled'] = True
                    module = plugin_obj['module']
                    if self.__has_method(module, 'on_start'):
                        self.__plugins_on_start.append(plugin_obj)
                    if self.__has_method(module, 'on_stop'):
                        self.__plugins_on_stop.append(plugin_obj)
                    if self.__has_method(module, 'on_exit'):
                        self.__plugins_on_exit.append(plugin_obj)
                    if self.__has_method(module, 'update_next_break', 2):
                        self.__plugins_update_next_break.append(plugin_obj)
            else:
                # This is the first time to load the plugin
                # Check for dependencies
                if Utility.check_plugin_dependencies(plugin['id'], plugin_config, plugin_path):
                    return

                # Load the plugin module
                module = importlib.import_module((plugin['id'] + '.plugin'))
                logging.info("Successfully loaded %s", str(module))
                plugin_obj = {'id': plugin['id'], 'module': module, 'config': dict(plugin.get(
                    'settings', {})), 'enabled': plugin_enabled, 'break_override_allowed': plugin_config.get('break_override_allowed', False)}
                # Inject the plugin directory into the config
                plugin_obj['config']['path'] = os.path.join(plugin_dir, plugin['id'])
                self.__plugins[plugin['id']] = plugin_obj
                if self.__has_method(module, 'enable'):
                    module.enable()
                if plugin_enabled:
                    if self.__has_method(module, 'on_start'):
                        self.__plugins_on_start.append(plugin_obj)
                    if self.__has_method(module, 'on_stop'):
                        self.__plugins_on_stop.append(plugin_obj)
                    if self.__has_method(module, 'on_exit'):
                        self.__plugins_on_exit.append(plugin_obj)
                    if self.__has_method(module, 'update_next_break', 2):
                        self.__plugins_update_next_break.append(plugin_obj)
                if self.__has_method(module, 'init', 3):
                    self.__plugins_on_init.append(plugin_obj)
                if self.__has_method(module, 'on_pre_break', 1):
                    self.__plugins_on_pre_break.append(plugin_obj)
                if self.__has_method(module, 'on_start_break', 1):
                    self.__plugins_on_start_break.append(plugin_obj)
                if self.__has_method(module, 'on_stop_break', 0):
                    self.__plugins_on_stop_break.append(plugin_obj)
                if self.__has_method(module, 'on_countdown', 2):
                    self.__plugins_on_countdown.append(plugin_obj)
                if self.__has_method(module, 'get_widget_title', 1) and self.__has_method(module, 'get_widget_content', 1):
                    self.__widget_plugins.append(plugin_obj)
                if self.__has_method(module, 'get_tray_action', 1):
                    self.__tray_actions_plugins.append(plugin_obj)
