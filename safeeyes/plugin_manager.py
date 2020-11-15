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
import logging
import os
import sys

from safeeyes import utility

sys.path.append(os.path.abspath(utility.SYSTEM_PLUGINS_DIR))
sys.path.append(os.path.abspath(utility.USER_PLUGINS_DIR))

HORIZONTAL_LINE_LENGTH = 64


class PluginManager:
    """
    Imports the Safe Eyes plugins and calls the methods defined in those plugins.
    """

    def __init__(self):
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
        Initialize all the plugins with init(context, safe_eyes_config, plugin_config) function.
        """
        # Load the plugins
        for plugin in config.get('plugins'):
            try:
                self.__load_plugin(plugin)
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

    def __load_plugin(self, plugin):
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
                utility.remove_if_exists(self.__plugins_on_start, plugin_obj)
                utility.remove_if_exists(self.__plugins_on_stop, plugin_obj)
                utility.remove_if_exists(self.__plugins_on_exit, plugin_obj)
                utility.remove_if_exists(self.__plugins_update_next_break, plugin_obj)
                # Call the plugin.disable method if available
                if utility.has_method(plugin_obj['module'], 'disable'):
                    plugin_obj['module'].disable()
                logging.info("Successfully unloaded the plugin '%s'", plugin['id'])

            if not plugin_obj['break_override_allowed']:
                # Remaining methods also should be removed
                utility.remove_if_exists(self.__plugins_on_init, plugin_obj)
                utility.remove_if_exists(self.__plugins_on_pre_break, plugin_obj)
                utility.remove_if_exists(self.__plugins_on_start_break, plugin_obj)
                utility.remove_if_exists(self.__plugins_on_stop_break, plugin_obj)
                utility.remove_if_exists(self.__plugins_on_countdown, plugin_obj)
                utility.remove_if_exists(self.__widget_plugins, plugin_obj)
                utility.remove_if_exists(self.__tray_actions_plugins, plugin_obj)
                del self.__plugins[plugin['id']]
            return

        # Look for plugin.py
        if os.path.isfile(os.path.join(utility.SYSTEM_PLUGINS_DIR, plugin['id'], 'plugin.py')):
            plugin_dir = utility.SYSTEM_PLUGINS_DIR
        elif os.path.isfile(os.path.join(utility.USER_PLUGINS_DIR, plugin['id'], 'plugin.py')):
            plugin_dir = utility.USER_PLUGINS_DIR
        else:
            logging.error('plugin.py not found for the plugin: %s', plugin['id'])
            return
        # Look for config.json
        plugin_path = os.path.join(plugin_dir, plugin['id'])
        plugin_config_path = os.path.join(plugin_path, 'config.json')
        if not os.path.isfile(plugin_config_path):
            logging.error('config.json not found for the plugin: %s', plugin['id'])
            return
        plugin_config = utility.load_json(plugin_config_path)
        if plugin_config is None:
            return

        if plugin_enabled or plugin_config.get('break_override_allowed', False):
            if plugin['id'] in self.__plugins:
                # The plugin is already enabled or partially loaded due to break_override_allowed

                # Validate the dependencies again
                if utility.check_plugin_dependencies(plugin['id'], plugin_config, plugin.get('settings', {}), plugin_path):
                    plugin_obj['enabled'] = False
                    utility.remove_if_exists(self.__plugins_on_start, plugin_obj)
                    utility.remove_if_exists(self.__plugins_on_stop, plugin_obj)
                    utility.remove_if_exists(self.__plugins_on_exit, plugin_obj)
                    utility.remove_if_exists(self.__plugins_update_next_break, plugin_obj)
                    utility.remove_if_exists(self.__plugins_on_init, plugin_obj)
                    utility.remove_if_exists(self.__plugins_on_pre_break, plugin_obj)
                    utility.remove_if_exists(self.__plugins_on_start_break, plugin_obj)
                    utility.remove_if_exists(self.__plugins_on_stop_break, plugin_obj)
                    utility.remove_if_exists(self.__plugins_on_countdown, plugin_obj)
                    utility.remove_if_exists(self.__widget_plugins, plugin_obj)
                    utility.remove_if_exists(self.__tray_actions_plugins, plugin_obj)
                    del self.__plugins[plugin['id']]

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
                    self.__init_plugin(module, plugin_obj)
            else:
                # This is the first time to load the plugin
                # Check for dependencies
                if utility.check_plugin_dependencies(plugin['id'], plugin_config, plugin.get('settings', {}), plugin_path):
                    return

                # Load the plugin module
                module = importlib.import_module((plugin['id'] + '.plugin'))
                logging.info("Successfully loaded %s", str(module))
                plugin_obj = {'id': plugin['id'], 'module': module, 'config': dict(plugin.get(
                    'settings', {})), 'enabled': plugin_enabled,
                              'break_override_allowed': plugin_config.get('break_override_allowed', False)}
                # Inject the plugin directory into the config
                plugin_obj['config']['path'] = os.path.join(plugin_dir, plugin['id'])
                self.__plugins[plugin['id']] = plugin_obj
                if utility.has_method(module, 'enable'):
                    module.enable()
                if plugin_enabled:
                    self.__init_plugin(module, plugin_obj)
                if utility.has_method(module, 'init', 3):
                    self.__plugins_on_init.append(plugin_obj)
                if utility.has_method(module, 'on_pre_break', 1):
                    self.__plugins_on_pre_break.append(plugin_obj)
                if utility.has_method(module, 'on_start_break', 1):
                    self.__plugins_on_start_break.append(plugin_obj)
                if utility.has_method(module, 'on_stop_break', 0):
                    self.__plugins_on_stop_break.append(plugin_obj)
                if utility.has_method(module, 'on_countdown', 2):
                    self.__plugins_on_countdown.append(plugin_obj)
                if utility.has_method(module, 'get_widget_title', 1) and utility.has_method(module,
                                                                                            'get_widget_content', 1):
                    self.__widget_plugins.append(plugin_obj)
                if utility.has_method(module, 'get_tray_action', 1):
                    self.__tray_actions_plugins.append(plugin_obj)

    def __init_plugin(self, module, plugin_obj):
        """
        Collect mandatory methods from the plugin and add them to the life cycle methods list.
        """
        if utility.has_method(module, 'on_start'):
            self.__plugins_on_start.append(plugin_obj)
        if utility.has_method(module, 'on_stop'):
            self.__plugins_on_stop.append(plugin_obj)
        if utility.has_method(module, 'on_exit'):
            self.__plugins_on_exit.append(plugin_obj)
        if utility.has_method(module, 'update_next_break', 2):
            self.__plugins_update_next_break.append(plugin_obj)
