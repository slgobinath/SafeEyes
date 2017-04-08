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
import babel.dates, os, errno, re, subprocess, threading, logging, locale, json
import pyaudio, wave

bin_directory = os.path.dirname(os.path.realpath(__file__))
home_directory = os.path.expanduser('~')
system_language_directory = os.path.join(bin_directory, "config/lang")
config_directory = os.path.join(home_directory, '.config/safeeyes')

"""
	Play the alert.wav
"""
def play_notification():
	logging.info("Playing audible alert")
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

"""
	Return the user-defined resource if a system resource is overridden by the user.
	Otherwise, return the system resource. Return None if the specified resource does not exist.
"""
def get_resource_path(resource_name):
	if resource_name is None:
		return None
	resource_location = os.path.join(config_directory, 'resource', resource_name)
	if not os.path.isfile(resource_location):
		resource_location = os.path.join(bin_directory, 'resource', resource_name)
		if not os.path.isfile(resource_location):
			logging.error('Resource not found: ' + resource_name)
			resource_location = None

	return resource_location


"""
	Get system idle time in minutes.
	Return the idle time if xprintidle is available, otherwise return 0.
"""
def system_idle_time():
	try:
		return int(subprocess.check_output(['xprintidle']).decode('utf-8')) / 60000	# Convert to minutes
	except:
		return 0


"""
	Execute the function in a separate thread.
"""
def start_thread(target_function, **args):
	thread = threading.Thread(target=target_function, kwargs=args)
	thread.start()


"""
	Execute the given function in main thread.
"""
def execute_main_thread(target_function, args=None):
	if args:
		GLib.idle_add(lambda: target_function(args))
	else:
		GLib.idle_add(lambda: target_function())


"""
	Check for full-screen applications.
	This method must be executed by the main thread. If not, it will cause to random failure.
"""
def is_active_window_skipped(skip_break_window_classes, take_break_window_classes, unfullscreen_allowed=False):
	logging.info("Searching for full-screen application")
	screen = Gdk.Screen.get_default()

	active_window = screen.get_active_window()
	if active_window:
		active_xid = str(active_window.get_xid())
		cmdlist = ['xprop', '-root', '-notype','-id',active_xid, 'WM_CLASS', '_NET_WM_STATE']

		try:
			stdout = subprocess.check_output(cmdlist).decode('utf-8')
		except subprocess.CalledProcessError:
			logging.warning("Error in finding full-screen application")
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


"""
	Return the system locale. If not available, return en_US.UTF-8.
"""
def __system_locale():
	locale.setlocale(locale.LC_ALL, '')
	system_locale = locale.getlocale(locale.LC_TIME)[0]
	if not system_locale:
		system_locale = 'en_US.UTF-8'
	return system_locale


"""
	Format time based on the system time.
"""
def format_time(time):
	system_locale = __system_locale()
	return babel.dates.format_time(time, format='short', locale=system_locale)


"""
	Create directory if not exists.
"""
def mkdir(path):
	try:
		os.makedirs(path)
	except OSError as exc:
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else:
			logging.error('Error while creating ' + str(path))
			raise

"""
	Convert the user defined language code to a valid one.
	This includes converting to lower case and finding system locale language,
	if the given lang_code code is 'system'.
"""
def parse_language_code(lang_code):
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


"""
	Load the desired language from the available list based on the preference.
"""
def load_language(lang_code):
	# Convert the user defined language code to a valid one
	lang_code = parse_language_code(lang_code)

	# Construct the translation file path
	language_file_path = os.path.join(system_language_directory, lang_code + '.json')

	language = None
	# Read the language file and construct the json object
	with open(language_file_path) as language_file:
		language = json.load(language_file)

	return language


"""
	Read all the language translations and build a key-value mapping of language names
	in English and ISO 639-1 (Filename without extension).
"""
def read_lang_files():
	languages = {}
	for lang_file_name in os.listdir(system_language_directory):
		lang_file_path = os.path.join(system_language_directory, lang_file_name)
		if os.path.isfile(lang_file_path):
			with open(lang_file_path) as lang_file:
				lang = json.load(lang_file)
				languages[lang_file_name.lower().replace('.json', '')] = lang['meta_info']['language_name']

	return languages

def desktop_envinroment():
	"""
	Function tries to detect current envinroment
	Possible results: unity, gnome or None if nothing detected
	"""
	if 'unity' == os.environ.get('XDG_CURRENT_DESKTOP', '').lower():
		return 'unity'
	elif 'gnome' == os.environ.get('DESKTOP_SESSION', '').lower():
		return 'gnome'
	
	return None

def is_desktop_lock_supported():
	return desktop_envinroment() in ['unity', 'gnome']

