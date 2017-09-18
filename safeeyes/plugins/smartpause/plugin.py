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

import logging, subprocess, threading
from safeeyes import Utility
from safeeyes.model import State

"""
Safe Eyes smart pause plugin
"""

context = None
idle_condition = threading.Condition()
lock = threading.Lock()
active = False
idle_time = 0
enable_safe_eyes = None
disable_safe_eyes = None
smart_pause_activated = False

def __system_idle_time():
	"""
	Get system idle time in minutes.
	Return the idle time if xprintidle is available, otherwise return 0.
	"""
	try:
		return int(subprocess.check_output(['xprintidle']).decode('utf-8')) / 60000    # Convert to minutes
	except:
		return 0


def __is_active():
	"""
	Thread safe function to see if this plugin is active or not.
	"""
	is_active = False
	with lock:
		is_active = active
	return is_active

def __set_active(is_active):
	"""
	Thread safe function to change the state of the plugin.
	"""
	global active
	with lock:
		active = is_active

def init(ctx, safeeyes_config, plugin_config):
	"""
	Initialize the plugin.
	"""
	global context
	global enable_safe_eyes
	global disable_safe_eyes
	global idle_time
	logging.debug('Initialize Smart Pause plugin')
	context = ctx
	enable_safe_eyes = context['api']['enable_safeeyes']
	disable_safe_eyes = context['api']['disable_safeeyes']
	idle_time = plugin_config['idle_time']

def __start_idle_monitor():
	"""
	Continuously check the system idle time and pause/resume Safe Eyes based on it.
	"""
	global smart_pause_activated
	while __is_active():
		# Wait for 2 seconds
		idle_condition.acquire()
		idle_condition.wait(2)
		idle_condition.release()

		if __is_active():
			# Get the system idle time
			system_idle_time = __system_idle_time()
			if system_idle_time >= idle_time and context['state'] == State.WAITING:
				smart_pause_activated = True
				logging.info('Pause Safe Eyes due to system idle')
				disable_safe_eyes()
			elif system_idle_time < idle_time and context['state'] == State.STOPPED:
				smart_pause_activated = False
				logging.info('Resume Safe Eyes due to user activity')
				enable_safe_eyes()

def on_start():
	"""
	Start a thread to continuously call xprintidle.
	"""
	global active
	if not __is_active():
		# If SmartPause is already started, do not start it again
		logging.debug('Start Smart Pause plugin')
		__set_active(True)
		Utility.start_thread(__start_idle_monitor)

def on_stop():
	"""
	Stop the thread from continuously calling xprintidle.
	"""
	global active
	global smart_pause_activated
	if smart_pause_activated:
		# Safe Eyes is stopped due to system idle
		smart_pause_activated = False
		return
	logging.debug('Stop Smart Pause plugin')
	__set_active(False)
	idle_condition.acquire()
	idle_condition.notify_all()
	idle_condition.release()
