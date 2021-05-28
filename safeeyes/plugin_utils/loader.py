#!/usr/bin/env python
# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2021  Gobinath

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
import importlib
import logging
import os
import sys
from typing import List, Any, Dict

from safeeyes import utility
from safeeyes.config import Config
from safeeyes.plugin_utils.proxy import PluginProxy
from safeeyes.utility import DESKTOP_ENVIRONMENT, CONFIG_RESOURCE

sys.path.append(os.path.abspath(utility.SYSTEM_PLUGINS_DIR))
sys.path.append(os.path.abspath(utility.USER_PLUGINS_DIR))


class PluginLoader:

    def __init__(self):
        self.__plugins: Dict[str, PluginProxy] = {}

    def load(self, config: Config) -> List[PluginProxy]:
        # Load the plugins
        for plugin in config.get('plugins'):
            try:
                self.__load_plugin(plugin)
            except BaseException:
                logging.exception('Error in loading the plugin: %s', plugin['id'])
                continue

        return list(self.__plugins.values())

    def __load_plugin(self, plugin: dict):
        """
        Load the given plugin.
        """
        plugin_id = plugin['id']
        plugin_enabled = plugin['enabled']
        if plugin_id in self.__plugins and not plugin_enabled:
            # Loading a disabled plugin but it was loaded earlier
            plugin_obj: PluginProxy = self.__plugins[plugin_id]
            plugin_obj.disable()
            if not plugin_obj.can_breaks_override():
                # Plugin is disabled and breaks cannot override it
                del self.__plugins[plugin_id]
            return

        # Look for plugin.py
        if os.path.isfile(os.path.join(utility.SYSTEM_PLUGINS_DIR, plugin_id, 'plugin.py')):
            plugin_dir = utility.SYSTEM_PLUGINS_DIR
        elif os.path.isfile(os.path.join(utility.USER_PLUGINS_DIR, plugin_id, 'plugin.py')):
            plugin_dir = utility.USER_PLUGINS_DIR
        else:
            logging.error('plugin.py not found for the plugin: %s', plugin_id)
            return

        # Look for config.json
        plugin_path = os.path.join(plugin_dir, plugin_id)
        plugin_config_path = os.path.join(plugin_path, 'config.json')
        if not os.path.isfile(plugin_config_path):
            logging.error('config.json not found for the plugin: %s', plugin_id)
            return

        # Read the plugin config.json
        plugin_config = utility.load_json(plugin_config_path)
        if plugin_config is None:
            logging.error('Failed to read config.json of the plugin: %s', plugin_id)
            return

        if plugin_enabled or plugin_config.get('break_override_allowed', False):
            if plugin_id in self.__plugins:
                # The plugin is already enabled or partially loaded due to break_override_allowed
                plugin_obj: PluginProxy = self.__plugins[plugin_id]
                # Validate the dependencies again
                if utility.check_plugin_dependencies(plugin_id, plugin_config, plugin.get('settings', {}),
                                                     plugin_path):
                    plugin_obj.disable()
                    del self.__plugins[plugin_id]
                    return

                # Update settings
                new_settings = dict(plugin.get('settings', {}))
                new_settings['path'] = os.path.join(plugin_dir, plugin_id)
                plugin_obj.update_settings(new_settings)
                plugin_obj.enable()
            else:
                # This is the first time to load the plugin
                # Check for dependencies
                if PluginLoader.__check_plugin_dependencies(plugin['id'], plugin_config, plugin.get('settings', {}),
                                                            plugin_path):
                    return

                # Load the plugin module
                module = importlib.import_module((plugin['id'] + '.plugin'))
                logging.info("Successfully loaded %s", str(module))
                plugin_obj = PluginProxy(plugin['id'], module, plugin_enabled, plugin_config,
                                         dict(plugin.get('settings', {})))
                self.__plugins[plugin['id']] = plugin_obj
                plugin_obj.enable()

    @staticmethod
    def __remove_if_exists(list_of_items: List, item: Any):
        """
        Remove the item from the list_of_items it it exists.
        """
        if item in list_of_items:
            list_of_items.remove(item)

    @staticmethod
    def __check_plugin_dependencies(plugin_id, plugin_config, plugin_settings, plugin_path):
        """
        Check the plugin dependencies.
        """
        # Check the desktop environment
        if plugin_config['dependencies']['desktop_environments']:
            # Plugin has restrictions on desktop environments
            if DESKTOP_ENVIRONMENT not in plugin_config['dependencies']['desktop_environments']:
                return _('Plugin does not support %s desktop environment') % DESKTOP_ENVIRONMENT

        # Check the Python modules
        for module in plugin_config['dependencies']['python_modules']:
            if not utility.module_exist(module):
                return _("Please install the Python module '%s'") % module

        # Check the shell commands
        for command in plugin_config['dependencies']['shell_commands']:
            if not utility.command_exist(command):
                return _("Please install the command-line tool '%s'") % command

        # Check the resources
        for resource in plugin_config['dependencies']['resources']:
            if utility.get_resource_path(resource) is None:
                return _('Please add the resource %(resource)s to %(config_resource)s directory') % {
                    'resource': resource, 'config_resource': CONFIG_RESOURCE}

        plugin_dependency_checker = os.path.join(plugin_path, 'dependency_checker.py')
        if os.path.isfile(plugin_dependency_checker):
            dependency_checker = importlib.import_module((plugin_id + '.dependency_checker'))
            if dependency_checker and hasattr(dependency_checker, "validate"):
                return dependency_checker.validate(plugin_config, plugin_settings)

        return None
