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
import os, subprocess, threading, logging

"""
	Play the alert.mp3
"""
def play_notification():
	logging.info("Playing audible alert")
	try:
		subprocess.Popen(['mpg123', '-q', os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resource/alert.mp3')])
	except:
		pass

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
def start_thread(target_function):
	thread = threading.Thread(target=target_function)
	thread.start()


"""
	Execute the given function in main thread.
"""
def execute_main_thread(target_function):
	GLib.idle_add(lambda: target_function())


"""
	Check for full-screen applications
"""
def is_full_screen_app_found():
	logging.info("Searching for full-screen application")
	screen = Gdk.Screen.get_default()
	active_xid = str(screen.get_active_window().get_xid())
	cmdlist = ['xprop', '-root', '-notype','-id',active_xid, '_NET_WM_STATE']
	
	try:
		stdout = subprocess.check_output(cmdlist)
	except subprocess.CalledProcessError:
		logging.warning("Error in finding full-screen application")
		pass
	else:
		if stdout:
			return 'FULLSCREEN' in stdout
