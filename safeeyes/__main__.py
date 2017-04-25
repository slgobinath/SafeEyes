#!/usr/bin/env python3

# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2016  Gobinath

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

import os, gi, json, dbus, logging, operator, psutil
from threading import Timer
from dbus.mainloop.glib import DBusGMainLoop
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from safeeyes.AboutDialog import AboutDialog
from safeeyes.BreakScreen import BreakScreen
from safeeyes.Notification import Notification
from safeeyes.Plugins import Plugins
from safeeyes.SafeEyesCore import SafeEyesCore
from safeeyes.SettingsDialog import SettingsDialog
from safeeyes.TrayIcon import TrayIcon
from safeeyes import Utility

# Define necessary paths
log_file_path = os.path.join(Utility.config_directory, 'safeeyes.log')
break_screen_glade = os.path.join(Utility.bin_directory, "glade/break_screen.glade")
settings_dialog_glade = os.path.join(Utility.bin_directory, "glade/settings_dialog.glade")
about_dialog_glade = os.path.join(Utility.bin_directory, "glade/about_dialog.glade")


is_active = True
SAFE_EYES_VERSION = "1.2.0a10"

"""
	Listen to tray icon Settings action and send the signal to Settings dialog.
"""
def show_settings():
	logging.info("Show Settings dialog")
	able_to_lock_screen = False
	if system_lock_command:
		able_to_lock_screen = True
	settings_dialog = SettingsDialog(config, language, Utility.read_lang_files(), able_to_lock_screen, save_settings, settings_dialog_glade)
	settings_dialog.show()

"""
	Listen to tray icon About action and send the signal to About dialog.
"""
def show_about():
	logging.info("Show About dialog")
	about_dialog = AboutDialog(about_dialog_glade, SAFE_EYES_VERSION, language)
	about_dialog.show()

"""
	Receive the signal from core and pass it to the Notification.
"""
def show_notification():
	if config['strict_break']:
		Utility.execute_main_thread(tray_icon.lock_menu)
	plugins.pre_notification(context)
	notification.show(config['pre_break_warning_time'])

"""
	Receive the break signal from core and pass it to the break screen.
"""
def show_alert(message, image_name):
	logging.info("Show the break screen")
	notification.close()
	plugins_data = plugins.pre_break(context)
	break_screen.show_message(message, Utility.get_resource_path(image_name), plugins_data)
	if config['strict_break'] and is_active:
		Utility.execute_main_thread(tray_icon.unlock_menu)

"""
	Receive the stop break signal from core and pass it to the break screen.
"""
def close_alert(audible_alert_on):
	logging.info("Close the break screen")
	if config['enable_screen_lock'] and context['break_type'] == 'long':
		# Lock the screen before closing the break screen
		Utility.lock_desktop(system_lock_command)
	break_screen.close()
	if audible_alert_on:
		Utility.play_notification()
	plugins.post_break(context)


"""
	Listen to the tray menu quit action and stop the core, notification and the app itself.
"""
def on_quit():
	logging.info("Quit Safe Eyes")
	plugins.exit(context)
	core.stop()
	notification.quite();
	Gtk.main_quit()

"""
	If the system goes to sleep, Safe Eyes stop the core if it is already active.
	If it was active, Safe Eyes will become active after wake up.
"""
def handle_suspend_callback(sleeping):
	if sleeping:
		# Sleeping / suspending
		if is_active:
			core.stop()
			logging.info("Stopped Safe Eyes due to system suspend")
	else:
		# Resume from sleep
		if is_active:
			core.start()
			logging.info("Resumed Safe Eyes after system wakeup")

"""
	Setup system suspend listener.
"""
def handle_system_suspend():
	DBusGMainLoop(set_as_default=True)
	bus = dbus.SystemBus()
	bus.add_signal_receiver(handle_suspend_callback, 'PrepareForSleep', 'org.freedesktop.login1.Manager', 'org.freedesktop.login1')

"""
	Listen to break screen Skip action and send the signal to core.
"""
def on_skipped():
	logging.info("User skipped the break")
	if config['enable_screen_lock'] and context['break_type'] == 'long' and context.get('count_down', 0) >= config['time_to_screen_lock']:
		# Lock the screen before closing the break screen
		Utility.lock_desktop(system_lock_command)
	core.skip_break()
	plugins.post_break(context)

"""
	Listen to break screen Postpone action and send the signal to core.
"""
def on_postponed():
	logging.info("User postponed the break")
	if config['enable_screen_lock'] and context['break_type'] == 'long' and context.get('count_down', 0) >= config['time_to_screen_lock']:
		# Lock the screen before closing the break screen
		Utility.lock_desktop(system_lock_command)
	core.postpone_break()

"""
	Listen to Settings dialog Save action and write to the config file.
"""
def save_settings(config):
	global language

	logging.info("Saving settings to safeeyes.json")

	# Stop the Safe Eyes core
	if is_active:
		core.stop()

	# Write the configuration to file
	with open(Utility.config_file_path, 'w') as config_file:
		json.dump(config, config_file, indent=4, sort_keys=True)

	# Reload the language translation
	language = Utility.load_language(config['language'])

	tray_icon.set_labels(language)

	logging.info("Initialize SafeEyesCore with modified settings")

	# Restart the core and intialize the components
	core.initialize(config, language)
	break_screen.initialize(config, language)
	if is_active:
		# 1 sec delay is required to give enough time for core to be stopped
		Timer(1.0, core.start).start()

"""
	Listen to tray icon enable action and send the signal to core.
"""
def enable_safeeyes():
	global is_active
	is_active = True
	core.start()

"""
	Listen to tray icon disable action and send the signal to core.
"""
def disable_safeeyes():
	global is_active
	is_active = False
	core.stop()


def running():
	"""
		Check if SafeEyes is already running.
	"""
	process_count = 0
	for proc in psutil.process_iter():
		try:
			# Check if safeeyes is in process arguments
			cmd_line = proc.cmdline()
			if 'python3' in cmd_line[0] and 'safeeyes' in cmd_line[1]:
				process_count += 1
				if process_count > 1:
					return True

		# Ignore if process does not exist or does not have command line args
		except (IndexError, psutil.NoSuchProcess):
			pass
	return False


def main():
	"""
	Start the Safe Eyes.
	"""

	# Create the directory to store log file if not exist
	if not os.path.exists(Utility.config_directory):
		try:
			os.makedirs(Utility.config_directory)
		except:
			pass

	# Configure logging.
	logging.basicConfig(format='%(asctime)s [%(levelname)s]:[%(threadName)s] %(message)s', filename=log_file_path, filemode='w', level=logging.INFO)
	logging.info("Starting Safe Eyes")

	if not running():

		global break_screen
		global core
		global config
		global notification
		global tray_icon
		global language
		global context
		global plugins
		global system_lock_command

		config = Utility.read_config()

		context = {}
		language = Utility.load_language(config['language'])
		# Get the lock command only one time
		if config['lock_screen_command']:
			system_lock_command = config['lock_screen_command']
		else:
			system_lock_command = Utility.lock_screen_command()


		# Initialize the Safe Eyes Context
		context['version'] = SAFE_EYES_VERSION

		tray_icon = TrayIcon(config, language, show_settings, show_about, enable_safeeyes, disable_safeeyes, on_quit)
		break_screen = BreakScreen(on_skipped, on_postponed, break_screen_glade, Utility.style_sheet_path)
		break_screen.initialize(config, language)
		notification = Notification(language)
		plugins = Plugins(config)
		core = SafeEyesCore(context, show_notification, show_alert, close_alert, break_screen.show_count_down, tray_icon.next_break_time)
		core.initialize(config, language)
		plugins.start(context)		# Call the start method of all plugins
		core.start()

		handle_system_suspend()

		Gtk.main()
	else:
		logging.info('SafeEyes is already running')
		sys.exit(0)

if __name__ == '__main__':
	main()
