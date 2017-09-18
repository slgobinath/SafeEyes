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

from AboutDialog import AboutDialog
from BreakScreen import BreakScreen
import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gettext
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import json
import logging
import os
from PluginManager import PluginManager
import psutil
from SafeEyesCore import SafeEyesCore
from SettingsDialog import SettingsDialog
import sys
from threading import Timer
import Utility as Utility

gettext.install('safeeyes', 'safeeyes/config/locale')


# Define necessary paths
break_screen_glade = os.path.join(Utility.bin_directory, "glade/break_screen.glade")
settings_dialog_glade = os.path.join(Utility.bin_directory, "glade/settings_dialog.glade")
about_dialog_glade = os.path.join(Utility.bin_directory, "glade/about_dialog.glade")

is_active = True
SAFE_EYES_VERSION = "2.0.0"


def show_settings():
	"""
	Listen to tray icon Settings action and send the signal to Settings dialog.
	"""
	logging.info("Show Settings dialog")
	able_to_lock_screen = False
	settings_dialog = SettingsDialog(config, language, Utility.read_lang_files(), able_to_lock_screen, save_settings, settings_dialog_glade)
	settings_dialog.show()


def show_about():
	"""
	Listen to tray icon About action and send the signal to About dialog.
	"""
	logging.info("Show About dialog")
	about_dialog = AboutDialog(about_dialog_glade, SAFE_EYES_VERSION, language)
	about_dialog.show()


def on_quit():
	"""
	Listen to the tray menu quit action and stop the core, notification and the app itself.
	"""
	logging.info("Quit Safe Eyes")
	plugins.stop()
	core.stop()
	Gtk.main_quit()


def handle_suspend_callback(sleeping):
	"""
	If the system goes to sleep, Safe Eyes stop the core if it is already active.
	If it was active, Safe Eyes will become active after wake up.
	"""
	if sleeping:
		# Sleeping / suspending
		if is_active:
			logging.info("Stop Safe Eyes due to system suspend")
			plugins.stop()
			core.stop()
	else:
		# Resume from sleep
		if is_active:
			logging.info("Resume Safe Eyes after system wakeup")
			plugins.start()
			core.start()


def handle_system_suspend():
	"""
	Setup system suspend listener.
	"""
	DBusGMainLoop(set_as_default=True)
	bus = dbus.SystemBus()
	bus.add_signal_receiver(handle_suspend_callback, 'PrepareForSleep', 'org.freedesktop.login1.Manager', 'org.freedesktop.login1')


def on_skipped():
	"""
	Listen to break screen Skip action and send the signal to core.
	"""
	logging.info("User skipped the break")
	core.skip()
	plugins.stop_break()


def on_postponed():
	"""
	Listen to break screen Postpone action and send the signal to core.
	"""
	logging.info("User postponed the break")
	core.postpone()
	plugins.stop_break()


def save_settings(config):
	"""
	Listen to Settings dialog Save action and write to the config file.
	"""
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

	logging.info("Initialize SafeEyesCore with modified settings")

	# Restart the core and intialize the components
	core.initialize(config, language)
	break_screen.initialize(config, language)
	if is_active:
		# 1 sec delay is required to give enough time for core to be stopped
		Timer(1.0, core.start).start()


def enable_safeeyes():
	"""
	Listen to tray icon enable action and send the signal to core.
	"""
	global is_active
	is_active = True
	core.start()
	plugins.start()


def disable_safeeyes():
	"""
	Listen to tray icon disable action and send the signal to core.
	"""
	global is_active
	is_active = False
	plugins.stop()
	core.stop()


def running():
	"""
	Check if SafeEyes is already running.
	"""
	process_count = 0
	for proc in psutil.process_iter():
		if not proc.cmdline:
			continue
		try:
			# Check if safeeyes is in process arguments
			if callable(proc.cmdline):
				# Latest psutil has cmdline function
				cmd_line = proc.cmdline()
			else:
				# In older versions cmdline was a list object
				cmd_line = proc.cmdline
			if ('python3' in cmd_line[0] or 'python' in cmd_line[0]) and ('safeeyes' in cmd_line[1] or 'safeeyes' in cmd_line):
				process_count += 1
				if process_count > 1:
					return True

		# Ignore if process does not exist or does not have command line args
		except (IndexError, psutil.NoSuchProcess):
			pass
	return False


def start_break(break_obj):
	if not plugins.start_break(break_obj):
		return False
	# Get the ASCII widgets content from plugins
	plugins_data = plugins.get_ascii_widgets(break_obj)
	break_screen.show_message(break_obj, plugins_data)
	return True


def countdown(countdown, seconds):
	break_screen.show_count_down(countdown, seconds)
	if not plugins.countdown(countdown, seconds):
		return False
	return True


def stop_break():
	break_screen.close()
	if not plugins.stop_break():
		return False
	return True


def main():
	"""
	Start the Safe Eyes.
	"""
	# Initialize the logging
	Utility.intialize_logging()

	logging.info("Starting Safe Eyes")

	if not running():

		global break_screen
		global core
		global config
		global language
		global context
		global plugins

		config = Utility.read_config()

		context = {}
		language = Utility.load_language(config['language'])
		# locale = gettext.translation('safeeyes', localedir='safeeyes/config/locale', languages=['ta'])
		locale = gettext.NullTranslations()
		locale.install()

		# Initialize the Safe Eyes Context
		context['version'] = SAFE_EYES_VERSION
		context['desktop'] = Utility.desktop_environment()
		context['language'] = language
		context['locale'] = locale
		context['api'] = {}
		context['api']['show_settings'] = show_settings
		context['api']['show_about'] = show_about
		context['api']['enable_safeeyes'] = enable_safeeyes
		context['api']['disable_safeeyes'] = disable_safeeyes
		context['api']['on_quit'] = on_quit

		break_screen = BreakScreen(context, on_skipped, on_postponed, break_screen_glade, Utility.style_sheet_path)
		break_screen.initialize(config, language)
		plugins = PluginManager(context, config)
		core = SafeEyesCore(context)
		core.on_pre_break += plugins.pre_break
		core.on_start_break += start_break
		core.on_count_down += countdown
		core.on_stop_break += stop_break
		core.on_update_next_break += plugins.update_next_break
		core.initialize(config, language)
		context['api']['take_break'] = core.take_break
		plugins.init(context, config)
		plugins.start()		# Call the start method of all plugins
		core.start()

		handle_system_suspend()

		Gtk.main()
	else:
		logging.info('Another instance of safeeyes is already running')
		sys.exit(0)


if __name__ == '__main__':
	main()
