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

import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib
from html.parser import HTMLParser
from distutils.version import LooseVersion
import babel.dates, os, errno, re, subprocess, threading, logging, locale, json, shutil, pyaudio, wave

bin_directory = os.path.dirname(os.path.realpath(__file__))
home_directory = os.path.expanduser('~')
system_language_directory = os.path.join(bin_directory, 'config/lang')
config_directory = os.path.join(home_directory, '.config/safeeyes')
config_file_path = os.path.join(config_directory, 'safeeyes.json')
style_sheet_path = os.path.join(config_directory, 'style/safeeyes_style.css')
system_config_file_path = os.path.join(bin_directory, "config/safeeyes.json")
system_style_sheet_path = os.path.join(bin_directory, "config/style/safeeyes_style.css")

def play_notification():
	"""
	Play the alert.wav
	"""
	logging.info('Playing audible alert')
	CHUNK = 1024

	try:
		# Open the sound file
		path = get_resource_path('alert.wav')
		if path is None:
			return
		sound = wave.open(path, 'rb')

		# Create a sound stream
		wrapper = pyaudio.PyAudio()
		stream = wrapper.open(format=wrapper.get_format_from_width(sound.getsampwidth()),
					channels=sound.getnchannels(),
					rate=sound.getframerate(),
						output=True)

		# Write file data into the sound stream
		data = sound.readframes(CHUNK)
		while data != b'':
			stream.write(data)
			data = sound.readframes(CHUNK)

		# Close steam
		stream.stop_stream()
		stream.close()
		sound.close()
		wrapper.terminate()

	except Exception as e:
		logging.warning('Unable to play audible alert')
		logging.exception(e)


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


def system_idle_time():
	"""
	Get system idle time in minutes.
	Return the idle time if xprintidle is available, otherwise return 0.
	"""
	try:
		return int(subprocess.check_output(['xprintidle']).decode('utf-8')) / 60000	# Convert to minutes
	except:
		return 0


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


def is_active_window_skipped(skip_break_window_classes, take_break_window_classes, unfullscreen_allowed=False):
	"""
	Check for full-screen applications.
	This method must be executed by the main thread. If not, it will cause to random failure.
	"""
	logging.info('Searching for full-screen application')
	screen = Gdk.Screen.get_default()

	active_window = screen.get_active_window()
	if active_window:
		active_xid = str(active_window.get_xid())
		cmdlist = ['xprop', '-root', '-notype','-id',active_xid, 'WM_CLASS', '_NET_WM_STATE']

		try:
			stdout = subprocess.check_output(cmdlist).decode('utf-8')
		except subprocess.CalledProcessError:
			logging.warning('Error in finding full-screen application')
			pass
		else:
			if stdout:
				is_fullscreen = 'FULLSCREEN' in stdout
				# Extract the process name
				process_names = re.findall('"(.+?)"', stdout)
				if process_names:
					process = process_names[1].lower()
					if process in skip_break_window_classes:
						return True
					elif process in take_break_window_classes:
						if is_fullscreen and unfullscreen_allowed:
							try:
								active_window.unfullscreen()
							except:
								logging.error('Error in unfullscreen the window ' + process)
								pass
						return False

				return is_fullscreen

	return False


def __system_locale():
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
	system_locale = __system_locale()
	return babel.dates.format_time(time, format='short', locale=system_locale)


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
		system_locale = __system_locale()
		lang_code = system_locale[0:2].lower()

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

def lock_screen_command():
	"""
	Function tries to detect the screensaver command based on the current envinroment
	Possible results:
		Gnome, Unity, Budgie:		['gnome-screensaver-command', '--lock']
		Cinnamon:					['cinnamon-screensaver-command', '--lock']
		Pantheon, LXDE:				['light-locker-command', '--lock']
		Mate:						['mate-screensaver-command', '--lock']
		KDE:						['qdbus', 'org.freedesktop.ScreenSaver', '/ScreenSaver', 'Lock']
		XFCE:						['xflock4']
		Otherwise:					None
	"""
	desktop_session = os.environ.get('DESKTOP_SESSION')
	current_desktop = os.environ.get('XDG_CURRENT_DESKTOP')
	if desktop_session is not None:
		desktop_session = desktop_session.lower()
		if ('xfce' in desktop_session or desktop_session.startswith('xubuntu') or (current_desktop is not None and 'xfce' in current_desktop)) and command_exist('xflock4'):
			return ['xflock4']
		elif desktop_session == 'cinnamon' and command_exist('cinnamon-screensaver-command'):
			return ['cinnamon-screensaver-command', '--lock']
		elif (desktop_session == 'pantheon' or desktop_session.startswith('lubuntu')) and command_exist('light-locker-command'):
			return ['light-locker-command', '--lock']
		elif desktop_session == 'mate' and command_exist('mate-screensaver-command'):
			return ['mate-screensaver-command', '--lock']
		elif desktop_session == 'kde' or 'plasma' in desktop_session or desktop_session.startswith('kubuntu') or os.environ.get('KDE_FULL_SESSION') == 'true':
			return ['qdbus', 'org.freedesktop.ScreenSaver', '/ScreenSaver', 'Lock']
		elif desktop_session in ['gnome','unity', 'budgie-desktop'] or desktop_session.startswith('ubuntu'):
			if command_exist('gnome-screensaver-command'):
				return ['gnome-screensaver-command', '--lock']
			else:
				# From Gnome 3.8 no gnome-screensaver-command
				return ['dbus-send', '--type=method_call', '--dest=org.gnome.ScreenSaver', '/org/gnome/ScreenSaver', 'org.gnome.ScreenSaver.Lock']
		elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
			if not 'deprecated' in os.environ.get('GNOME_DESKTOP_SESSION_ID') and command_exist('gnome-screensaver-command'):
				# Gnome 2
				return ['gnome-screensaver-command', '--lock']
	return None


def lock_desktop(command):
	"""
	Lock the screen using the predefined commands
	"""
	if command:
		try:
			subprocess.Popen(command)
		except Exception as e:
			logging.error('Error in executing the commad' + str(command) + ' to lock screen')


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
	except:
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
		self.convert_charrefs= True
		self.fed = []

	def handle_data(self, d):
		self.fed.append(d)

	def get_data(self):
		return ''.join(self.fed)
