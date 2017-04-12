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

import logging, importlib, os, sys, inspect, copy
from multiprocessing import Pool, TimeoutError
from safeeyes import Utility

plugins_directory = os.path.join(Utility.config_directory, 'plugins')
sys.path.append(os.path.abspath(plugins_directory))

class Plugins:
	"""
		This class manages imports the plugins and calls the methods defined in those plugins.
	"""


	def __init__(self, config):
		"""
		Load the plugins.
		"""
		logging.info('Load all the plugins')
		self.__plugins = []
		self.__thread_pool = Pool(processes=4)

		for plugin in config['plugins']:
			if plugin['location'].lower() in ['left', 'right']:
				if os.path.isfile(os.path.join(plugins_directory, plugin['name'] + '.py')):
					module = importlib.import_module(plugin['name'])
					if self.__has_method(module, 'start') and self.__has_method(module, 'pre_notification') and self.__has_method(module, 'pre_break') and self.__has_method(module, 'post_break') and self.__has_method(module, 'exit'):
						self.__plugins.append({'module': module, 'location': plugin['location'].lower()})
					else:
						logging.warning('Ignoring the plugin ' + str(plugin['name']) + ' due to invalid method signature')
				else:
					logging.warning('Plugin file ' + str(plugin['name']) + '.py not found')
			else:
				logging.warning('Ignoring the plugin ' + str(plugin['name']) + ' due to invalid location value: ' +  plugin['location'])


	def start(self, context):
		"""
		Call the start function of all the plugins in separate thread.
		"""
		context = copy.deepcopy(context)	# If plugins change the context, it should not affect Safe Eyes
		for plugin in self.__plugins:
			try:
				self.__thread_pool.apply_async(plugin['module'].start, (context,))
			except Exception as e:
				pass

	def pre_notification(self, context):
		"""
		Call the pre_notification function of all the plugins in separate thread.
		"""
		context = copy.deepcopy(context)	# If plugins change the context, it should not affect Safe Eyes
		for plugin in self.__plugins:
			try:
				self.__thread_pool.apply_async(plugin['module'].pre_notification, (context,))
			except Exception as e:
				pass


	def pre_break(self, context):
		"""
		Call the pre_break function of all the plugins and provide maximum 1 second to return the result.
		If they return the reault within 1 sec, append it to the output.

		Returns: {'left': 'Markup of plugins to be aligned on left', 'right': 'Markup of plugins to be aligned on right' }
		"""
		context = copy.deepcopy(context)	# If plugins change the context, it should not affect Safe Eyes
		output = {'left': '', 'right': ''}
		multiple_results = [self.__thread_pool.apply_async(plugin['module'].pre_break, (context,)) for plugin in self.__plugins]
		for i in range(len(multiple_results)):
			try:
				result = multiple_results[i].get(timeout=1)
				if result:
					output[self.__plugins[i]['location']] += (result + '\n\n')
			except TimeoutError:
				# Plugin took too much of time
				pass
			except Exception:
				# Something went wrong in the plugin
				pass

		return output


	def post_break(self, context):
		"""
		Call the post_break function of all the plugins in separate thread.
		"""
		context = copy.deepcopy(context)	# If plugins change the context, it should not affect Safe Eyes
		for plugin in self.__plugins:
			try:
				self.__thread_pool.apply_async(plugin['module'].post_break, (context,))
			except Exception as e:
				pass

	def exit(self, context):
		"""
		Call the exit function of all the plugins in separate thread.
		"""
		context = copy.deepcopy(context)	# If plugins change the context, it should not affect Safe Eyes
		for plugin in self.__plugins:
			try:
				self.__thread_pool.apply_async(plugin['module'].exit, (context,))
			except Exception as e:
				pass


	def __has_method(self, module, method_name, no_of_args = 1):
		"""
		Check whether the given function is defined in the module or not.
		"""
		if hasattr(module, method_name):
			if len(inspect.getargspec(getattr(module, method_name)).args) == no_of_args:
				return True
		return False
