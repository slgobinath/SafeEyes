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

import babel.dates
from distutils.version import LooseVersion
import errno
import gi
gi.require_version('Gdk', '3.0')
from gi.repository import GLib
from html.parser import HTMLParser
import imp
import json
import locale
import logging
import os
import shutil
import subprocess
import threading

bin_directory = os.path.dirname(os.path.realpath(__file__))
home_directory = os.path.expanduser('~')
system_language_directory = os.path.join(bin_directory, 'config/lang')
config_directory = os.path.join(home_directory, '.config/safeeyes')
config_file_path = os.path.join(config_directory, 'safeeyes.json')
style_sheet_path = os.path.join(config_directory, 'style/safeeyes_style.css')
system_config_file_path = os.path.join(bin_directory, "config/safeeyes.json")
system_style_sheet_path = os.path.join(bin_directory, "config/style/safeeyes_style.css")
log_file_path = os.path.join(config_directory, 'safeeyes.log')
pyaudio = None


def import_dependencies():
	"""
	Import the optional Python dependencies.
	"""
	try:
		# Import pyaudio if exists
		global pyaudio
		pyaudio = __import__("pyaudio")
	except ImportError:
		logging.warning('Install pyaudio for audible notifications.')


def get_resource_path(resource_name):
	"""
	Return the user-defined resource if a system resource is overridden by the user.
	Otherwise, return the system resource. Return None if the specified resource does not exist.
	"""
	if resource_name is None:
		return None
	resource_location = os.path.join(config_directory, 'resource', resource_name)
	if not os.path.isfile(resource_location):
		resource_location = os.path.join(bin_directory, 'resource', resource_name)
		if not os.path.isfile(resource_location):
			logging.error('Resource not found: ' + resource_name)
			resource_location = None

	return resource_location


def start_thread(target_function, **args):
	"""
	Execute the function in a separate thread.
	"""
	thread = threading.Thread(target=target_function, kwargs=args)
	thread.start()


def execute_main_thread(target_function, args=None):
	"""
	Execute the given function in main thread.
	"""
	if args:
		GLib.idle_add(lambda: target_function(args))
	else:
		GLib.idle_add(lambda: target_function())


def system_locale():
	"""
	Return the system locale. If not available, return en_US.UTF-8.
	"""
	locale.setlocale(locale.LC_ALL, '')
	system_locale = locale.getlocale(locale.LC_TIME)[0]
	if not system_locale:
		system_locale = 'en_US.UTF-8'
	return system_locale


def format_time(time):
	"""
	Format time based on the system time.
	"""
	sys_locale = system_locale()
	return babel.dates.format_time(time, format='short', locale=sys_locale)


def mkdir(path):
	"""
	Create directory if not exists.
	"""
	try:
		os.makedirs(path)
	except OSError as exc:
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else:
			logging.error('Error while creating ' + str(path))
			raise


def parse_language_code(lang_code):
	"""
	Convert the user defined language code to a valid one.
	This includes converting to lower case and finding system locale language,
	if the given lang_code code is 'system'.
	"""
	# Convert to lower case
	lang_code = str(lang_code).lower()

	# If it is system, use the system language
	if lang_code == 'system':
		logging.info('Use system language for Safe Eyes')
		locale = system_locale()
		lang_code = locale[0:2].lower()

	# Check whether translation is available for this language.
	# If not available, use English by default.
	language_file_path = os.path.join(system_language_directory, lang_code + '.json')
	if not os.path.exists(language_file_path):
		logging.warn('The language {} does not exist. Use English instead'.format(lang_code))
		lang_code = 'en'

	return lang_code


def load_language(lang_code):
	"""
	Load the desired language from the available list based on the preference.
	"""
	# Convert the user defined language code to a valid one
	lang_code = parse_language_code(lang_code)

	# Construct the translation file path
	language_file_path = os.path.join(system_language_directory, lang_code + '.json')

	language = None
	# Read the language file and construct the json object
	with open(language_file_path) as language_file:
		language = json.load(language_file)

	return language


def read_lang_files():
	"""
	Read all the language translations and build a key-value mapping of language names
	in English and ISO 639-1 (Filename without extension).
	"""
	languages = {}
	for lang_file_name in os.listdir(system_language_directory):
		lang_file_path = os.path.join(system_language_directory, lang_file_name)
		if os.path.isfile(lang_file_path):
			with open(lang_file_path) as lang_file:
				lang = json.load(lang_file)
				languages[lang_file_name.lower().replace('.json', '')] = lang['meta_info']['language_name']

	return languages


def desktop_environment():
	"""
	Detect the desktop environment.
	"""
	desktop_session = os.environ.get('DESKTOP_SESSION')
	current_desktop = os.environ.get('XDG_CURRENT_DESKTOP')
	if desktop_session is not None:
		desktop_session = desktop_session.lower()
		if desktop_session in ['gnome', 'unity', 'budgie-desktop', 'cinnamon', 'mate', 'xfce4', 'lxde', 'pantheon', 'fluxbox', 'blackbox', 'openbox', 'icewm', 'jwm', 'afterstep', 'trinity', 'kde']:
			return desktop_session
		elif (desktop_session.startswith('xubuntu') or (current_desktop is not None and 'xfce' in current_desktop)):
			return 'xfce'
		elif desktop_session.startswith('ubuntu'):
			return 'unity'
		elif desktop_session.startswith('lubuntu'):
			return 'lxde'
		elif 'plasma' in desktop_session or desktop_session.startswith('kubuntu') or os.environ.get('KDE_FULL_SESSION') == 'true':
			return 'kde'
		elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
			return 'gnome'
	return 'unknown'


def execute_command(command, args=[]):
	"""
	Execute the shell command without waiting for its response.
	"""
	if command:
		command_to_execute = []
		if isinstance(command, str):
			command_to_execute.append(command)
		else:
			command_to_execute.extend(command)
		if args:
			command_to_execute.extend(args)
		try:
			subprocess.Popen(command_to_execute)
		except Exception as e:
			logging.error('Error in executing the commad' + str(command))


def html_to_text(html):
	"""
	Convert HTML to plain text
	"""
	extractor = __HTMLTextExtractor()
	extractor.feed(html)
	return extractor.get_data()


def command_exist(command):
	"""
	Check whether the given command exist in the system or not.
	"""
	if shutil.which(command):
		return True
	else:
		return False


def module_exist(module):
	"""
	Check wther the given Python module exists or not.
	"""
	try:
		imp.find_module(module)
		return True
	except ImportError:
		return False


def merge_configs(new_config, old_config):
	"""
	Merge the values of old_config into the new_config.
	"""
	new_config = new_config.copy()
	new_config.update(old_config)
	return new_config


def __initialize_safeeyes():
	"""
	Create the config file and style sheet in ~/.config/safeeyes directory.
	"""
	logging.info('Copy the config files to ~/.config/safeeyes')

	style_dir_path = os.path.join(home_directory, '.config/safeeyes/style')
	startup_dir_path = os.path.join(home_directory, '.config/autostart')

	# Remove the ~/.config/safeeyes directory
	shutil.rmtree(config_directory, ignore_errors=True)

	# Remove the startup file
	try:
		os.remove(os.path.join(home_directory, os.path.join(startup_dir_path, 'safeeyes.desktop')))
	except Exception:
		pass

	# Create the ~/.config/safeeyes/style directory
	mkdir(style_dir_path)
	mkdir(startup_dir_path)

	# Copy the safeeyes.json
	shutil.copy2(system_config_file_path, config_file_path)

	# Copy the new startup file
	try:
		os.symlink("/usr/share/applications/safeeyes.desktop", os.path.join(startup_dir_path, 'safeeyes.desktop'))
	except OSError as exc:
		pass

	# Copy the new style sheet
	if not os.path.isfile(style_sheet_path):
		shutil.copy2(system_style_sheet_path, style_sheet_path)


def intialize_logging():
	"""
	Initialize the logging framework using the Safe Eyes specific configurations.
	"""
	# Create the directory to store log file if not exist
	if not os.path.exists(config_directory):
		try:
			os.makedirs(config_directory)
		except Exception:
			pass

	# Configure logging.
	log_formatter = logging.Formatter('%(asctime)s [%(levelname)s]:[%(threadName)s] %(message)s')

	# Apped the logs and overwrite once reached 5MB
	handler = logging.StreamHandler()  # RotatingFileHandler(log_file_path, mode='a', maxBytes=5 * 1024 * 1024, backupCount=2, encoding=None, delay=0)
	handler.setFormatter(log_formatter)
	handler.setLevel(logging.DEBUG)

	root_logger = logging.getLogger()
	root_logger.setLevel(logging.DEBUG)
	root_logger.addHandler(handler)


def read_config():
	"""
	Read the configuration from the config directory.
	If does not exist or outdated by major version, copy the system config and
	startup script to user directory.
	If the user config is outdated by minor version, update the config by the new values.
	"""
	logging.info('Reading the configuration file')

	if not os.path.isfile(config_file_path):
		logging.info('Safe Eyes configuration file not found')
		__initialize_safeeyes()

	# Read the configurations
	with open(config_file_path) as config_file:
		user_config = json.load(config_file)

	with open(system_config_file_path) as config_file:
		system_config = json.load(config_file)

	user_config_version = str(user_config['meta']['config_version'])
	system_config_version = str(system_config['meta']['config_version'])

	if LooseVersion(user_config_version) < LooseVersion(system_config_version):
		# Outdated user config
		logging.info('Update the old config version {} with new config version {}'.format(user_config_version, system_config_version))
		user_config_major_version = user_config_version.split('.')[0]
		system_config_major_version = system_config_version.split('.')[0]

		if LooseVersion(user_config_major_version) < LooseVersion(system_config_major_version):
			# Major version change
			__initialize_safeeyes()
			# Update the user_config
			user_config = system_config
		else:
			# Minor version change
			new_config = system_config.copy()
			new_config.update(user_config)
			# Update the version
			new_config['meta']['config_version'] = system_config_version

			# Write the configuration to file
			with open(config_file_path, 'w') as config_file:
				json.dump(new_config, config_file, indent=4, sort_keys=True)

			# Update the user_config
			user_config = new_config

	return user_config


class __HTMLTextExtractor(HTMLParser):
	"""
	Helper class to convert HTML to text
	"""
	def __init__(self):
		self.reset()
		self.strict = False
		self.convert_charrefs = True
		self.fed = []

	def handle_data(self, d):
		self.fed.append(d)

	def get_data(self):
		return ''.join(self.fed)
