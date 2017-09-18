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

import importlib
import inspect
import json
import logging
import os
from safeeyes import Utility
import sys

system_plugins_directory = os.path.join(Utility.bin_directory, 'plugins')
plugins_directory = os.path.join(Utility.config_directory, 'plugins')
sys.path.append(os.path.abspath(system_plugins_directory))
# sys.path.append(os.path.abspath(plugins_directory))


class PluginManager(object):
	"""
	Imports the Safe Eyes plugins and calls the methods defined in those plugins.
	"""

	def __init__(self, context, config):
		logging.info('Load all the plugins')
		self.__plugins_on_init = []
		self.__plugins_on_start = []
		self.__plugins_on_stop = []
		self.__plugins_on_pre_break = []
		self.__plugins_on_start_break = []
		self.__plugins_on_stop_break = []
		self.__plugins_on_countdown = []
		self.__plugins_update_next_break = []
		self.__widget_plugins = []

		for plugin in config['plugins']:

			if plugin['enabled']:  # and os.path.isfile(os.path.join(system_plugins_directory, plugin['id'], plugin['id'] + '.py')):
				# System plugin found
				plugin_config_path = os.path.join(system_plugins_directory, plugin['id'], 'config.json')
				if not os.path.isfile(plugin_config_path):
					logging.error('config.json not found for the plugin: {}'.format(plugin['id']))
					continue
				with open(plugin_config_path) as config_file:
					plugin_config = json.load(config_file)

				# Check for dependencies
				dependencies_satisfied = True
				# Check the Python modules
				for module in plugin_config['dependencies']['python_modules']:
					if not Utility.module_exist(module):
						dependencies_satisfied = False
						break

				# Check the shell commands
				for command in plugin_config['dependencies']['shell_commands']:
					if not Utility.command_exist(command):
						dependencies_satisfied = False
						break

				# Check the desktop environment
				if plugin_config['dependencies']['desktop_environments']:
					# Plugin has restrictions on desktop environments
					if context['desktop'] not in plugin_config['dependencies']['desktop_environments']:
						dependencies_satisfied = False

				if not dependencies_satisfied:
					continue

				# Load the plugin module
				module = importlib.import_module((plugin['id'] + '.plugin'))
				plugin_obj = {'module': module, 'config': plugin.get('settings', {}), 'location': None}
				logging.info("Loading {}".format(str(module)))
				if self.__has_method(module, 'init', 3):
					self.__plugins_on_init.append(plugin_obj)
				if self.__has_method(module, 'on_start'):
					self.__plugins_on_start.append(plugin_obj)
				if self.__has_method(module, 'on_stop'):
					self.__plugins_on_stop.append(plugin_obj)
				if self.__has_method(module, 'on_pre_break', 1):
					self.__plugins_on_pre_break.append(plugin_obj)
				if self.__has_method(module, 'on_start_break', 1):
					self.__plugins_on_start_break.append(plugin_obj)
				if self.__has_method(module, 'on_stop_break', 0):
					self.__plugins_on_stop_break.append(plugin_obj)
				if self.__has_method(module, 'on_countdown', 2):
					self.__plugins_on_countdown.append(plugin_obj)
				if self.__has_method(module, 'update_next_break', 1):
					self.__plugins_update_next_break.append(plugin_obj)
				if self.__has_method(module, 'get_content') and 'location' in plugin:
					plugin_obj['location'] = plugin['location'].lower()
					self.__widget_plugins.append(plugin_obj)

	def init(self, context, config):
		"""
		Initialize all the plugins with init(context, safeeyes_config, plugin_config) function.
		"""
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

	def pre_break(self, break_obj):
		"""
		Execute the on_pre_break(break_obj) function of plugins.
		"""
		for plugin in self.__plugins_on_pre_break:
			if plugin['module'].on_pre_break(break_obj):
				return False
		return True

	def start_break(self, break_obj):
		"""
		Execute the start_break(break_obj) function of plugins.
		"""
		for plugin in self.__plugins_on_start_break:
			if plugin['module'].on_start_break(break_obj):
				return False

		return True

	def stop_break(self):
		"""
		Execute the stop_break() function of plugins.
		"""
		for plugin in self.__plugins_on_stop_break:
			plugin['module'].on_stop_break()
		return True

	def countdown(self, countdown, seconds):
		"""
		Execute the on_countdown(countdown, seconds) function of plugins.
		"""
		logging.debug("Countdown: elapsed " + str(countdown) + " seconds, " + str(seconds) + " seconds to go")
		for plugin in self.__plugins_on_countdown:
			plugin['module'].on_countdown(countdown, seconds)
		return True

	def update_next_break(self, break_time):
		"""
		Execute the update_next_break(break_time) function of plugins.
		"""
		for plugin in self.__plugins_update_next_break:
			plugin['module'].update_next_break(break_time)
		return True

	def get_ascii_widgets(self, break_obj):
		"""
		Returns: {'left': 'Markup of plugins to be aligned on left', 'right': 'Markup of plugins to be aligned on right' }
		"""
		output = {'left': '                                                  \n', 'right': '                                                  \n'}
		return output

	def __has_method(self, module, method_name, no_of_args=0):
		"""
		Check whether the given function is defined in the module or not.
		"""
		if hasattr(module, method_name):
			if len(inspect.getargspec(getattr(module, method_name)).args) == no_of_args:
				return True
		return False
