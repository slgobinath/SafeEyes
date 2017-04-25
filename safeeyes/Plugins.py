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
from multiprocessing.pool import ThreadPool
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

		for plugin in config['plugins']:
			if plugin['location'].lower() in ['left', 'right']:
				if os.path.isfile(os.path.join(plugins_directory, plugin['name'] + '.py')):
					module = importlib.import_module(plugin['name'])
					if self.__has_method(module, 'start') and self.__has_method(module, 'pre_notification') and self.__has_method(module, 'pre_break') and self.__has_method(module, 'post_break') and self.__has_method(module, 'exit'):
						self.__plugins.append({'name': plugin['name'], 'module': module, 'location': plugin['location'].lower()})
					else:
						logging.warning('Ignoring the plugin ' + str(plugin['name']) + ' due to invalid method signature')
				else:
					logging.warning('Plugin file ' + str(plugin['name']) + '.py not found')
			else:
				logging.warning('Ignoring the plugin ' + str(plugin['name']) + ' due to invalid location value: ' +  plugin['location'])
		
		if self.__plugins:
			self.__thread_pool = ThreadPool(min([4, len(self.__plugins)]))


	def start(self, context):
		"""
		Call the start function of all the plugins in separate thread.
		"""
		if self.__plugins:
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
		if self.__plugins:
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
		output = {'left': '                                                  \n', 'right': '                                                  \n'}
		if self.__plugins:
			context = copy.deepcopy(context)	# If plugins change the context, it should not affect Safe Eyes
			multiple_results = [self.__thread_pool.apply_async(plugin['module'].pre_break, (context,)) for plugin in self.__plugins]
			for i in range(len(multiple_results)):
				try:
					result = multiple_results[i].get(timeout=1)
					if result:
						# Limit the line length to 50 characters
						large_lines  = list(filter(lambda x: len(x) > 50, Utility.html_to_text(result).splitlines()))
						if large_lines:
							logging.warning('Ignoring lengthy result from the plugin ' + self.__plugins[i]['name'])
							continue
						output[self.__plugins[i]['location']] += (result + '\n\n')
				except Exception:
					# Something went wrong in the plugin
					logging.warning('Error when executing the plugin ' + self.__plugins[i]['name'])

		return output


	def post_break(self, context):
		"""
		Call the post_break function of all the plugins in separate thread.
		"""
		if self.__plugins:
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
		if self.__plugins:
			context = copy.deepcopy(context)	# If plugins change the context, it should not affect Safe Eyes

			# Give maximum 1 sec for all plugins before terminating the thread pool
			multiple_results = [self.__thread_pool.apply_async(plugin['module'].exit, (context,)) for plugin in self.__plugins]
			for i in range(len(multiple_results)):
				try:
					multiple_results[i].get(timeout=1)
				except Exception:
					# Something went wrong in the plugin
					pass

			try:
				self.__thread_pool.terminate()	# Shutdown the pool
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
