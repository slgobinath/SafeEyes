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
from typing import List, Any, Dict, Optional

from safeeyes import utility, SAFE_EYES_HOME_DIR, SAFE_EYES_CONFIG_DIR
from safeeyes.config import Config
from safeeyes.context import Context
from safeeyes.env import system
from safeeyes.plugin_utils.plugin import Validator
from safeeyes.plugin_utils.proxy import PluginProxy, ValidatorProxy
from safeeyes.util.locale import _
from safeeyes.utility import DESKTOP_ENVIRONMENT, CONFIG_RESOURCE

sys.path.append(os.path.abspath(utility.SYSTEM_PLUGINS_DIR))
sys.path.append(os.path.abspath(utility.USER_PLUGINS_DIR))

SYSTEM_PLUGINS_DIR = os.path.join(SAFE_EYES_HOME_DIR, 'plugins')
USER_PLUGINS_DIR = os.path.join(SAFE_EYES_CONFIG_DIR, 'plugins')


class PluginLoader:

    def __init__(self):
        self.__plugins: Dict[str, PluginProxy] = {}

    def load(self, context: Context) -> List[PluginProxy]:
        # Load the plugins
        for plugin in context.config.get('plugins'):
            try:
                self.__load_plugin(context, plugin)
            except BaseException:
                logging.exception('Error in loading the plugin: %s', plugin['id'])
                continue

        return list(self.__plugins.values())

    def __load_plugin(self, context: Context, plugin: dict):
        """
        Load the given plugin.
        """
        plugin_obj: PluginProxy
        plugin_id = plugin['id']
        plugin_enabled = plugin['enabled']
        if plugin_id in self.__plugins and not plugin_enabled:
            # Loading a disabled plugin but it was loaded earlier
            plugin_obj = self.__plugins[plugin_id]
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
                plugin_obj = self.__plugins[plugin_id]
                # Validate the dependencies again
                if PluginLoader.__check_plugin_dependencies(context, plugin_id, plugin_config,
                                                            plugin.get('settings', {}), plugin_path):
                    plugin_obj.disable()
                    del self.__plugins[plugin_id]
                    return

                # Update settings
                new_settings = dict(plugin.get('settings', {}))
                new_settings['path'] = os.path.join(plugin_dir, plugin_id)
                plugin_obj.update_settings(new_settings)
            else:
                # This is the first time to load the plugin
                # Check for dependencies
                if PluginLoader.__check_plugin_dependencies(context, plugin['id'], plugin_config,
                                                            plugin.get('settings', {}), plugin_path):
                    return

                # Load the plugin module
                module = importlib.import_module((plugin['id'] + '.plugin'))
                logging.info("Successfully loaded '%s' plugin from '%s'", plugin['id'], str(module.__file__))
                new_settings = dict(plugin.get('settings', {}))
                new_settings['path'] = os.path.join(plugin_dir, plugin_id)
                plugin_obj = PluginProxy(plugin['id'], module, False, plugin_config, new_settings)
                self.__plugins[plugin['id']] = plugin_obj

            if plugin_enabled:
                plugin_obj.enable()

    @staticmethod
    def load_plugins_config(context: Context, config: Config) -> List[dict]:
        """
        Load all the plugins from the given directory.
        """
        configs: List[dict] = []
        for plugin in config.get('plugins'):
            plugin_path = os.path.join(SYSTEM_PLUGINS_DIR, plugin['id'])
            if not os.path.isdir(plugin_path):
                # User plugin
                plugin_path = os.path.join(USER_PLUGINS_DIR, plugin['id'])
            plugin_config_path = os.path.join(plugin_path, 'config.json')
            plugin_icon_path = os.path.join(plugin_path, 'icon.png')
            plugin_module_path = os.path.join(plugin_path, 'plugin.py')
            if not os.path.isfile(plugin_module_path):
                return []
            icon = None
            if os.path.isfile(plugin_icon_path):
                icon = plugin_icon_path
            else:
                icon = system.get_resource_path('ic_plugin.png')
            plugin_config = utility.load_json(plugin_config_path)
            if plugin_config is None:
                continue
            dependency_description = PluginLoader.__check_plugin_dependencies(context, plugin['id'], plugin_config,
                                                                              plugin.get('settings', {}), plugin_path)
            if dependency_description:
                plugin['enabled'] = False
                plugin_config['error'] = True
                plugin_config['meta']['description'] = dependency_description
                icon = system.get_resource_path('ic_warning.png')
            else:
                plugin_config['error'] = False
            plugin_config['id'] = plugin['id']
            plugin_config['icon'] = icon
            plugin_config['enabled'] = plugin['enabled']
            for setting in plugin_config['settings']:
                setting['safeeyes_config'] = plugin['settings']
            configs.append(plugin_config)
        return configs

    @staticmethod
    def __remove_if_exists(list_of_items: List, item: Any):
        """
        Remove the item from the list_of_items it it exists.
        """
        if item in list_of_items:
            list_of_items.remove(item)

    @staticmethod
    def __check_plugin_dependencies(context: Context, plugin_id: str, plugin_config: dict, plugin_settings: dict,
                                    plugin_path: str) -> Optional[str]:
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
            if not system.module_exists(module):
                return _("Please install the Python module '%s'") % module

        # Check the shell commands
        for command in plugin_config['dependencies']['shell_commands']:
            if not system.command_exists(command):
                return _("Please install the command-line tool '%s'") % command

        # Check the resources
        for resource in plugin_config['dependencies']['resources']:
            if utility.get_resource_path(resource) is None:
                return _('Please add the resource %(resource)s to %(config_resource)s directory') % {
                    'resource': resource, 'config_resource': CONFIG_RESOURCE}

        validator = PluginLoader.__get_validator(plugin_id, plugin_path)
        if validator:
            return validator.validate(context, plugin_config, plugin_settings)

        return None

    @staticmethod
    def __get_validator(plugin_id: str, plugin_path: str) -> Optional[Validator]:
        plugin_validator = os.path.join(plugin_path, 'validator.py')
        if os.path.isfile(plugin_validator):
            validator = importlib.import_module((plugin_id + '.validator'))
            return ValidatorProxy(validator)
        return None
