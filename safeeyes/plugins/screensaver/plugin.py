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

import logging
import os

from safeeyes import Utility

"""
Safe Eyes Screensaver plugin
"""

context = None
lock_screen = False
lock_screen_command = None
min_seconds = 0
seconds_passed = 0


def __lock_screen_command():
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
		if ('xfce' in desktop_session or desktop_session.startswith('xubuntu') or (current_desktop is not None and 'xfce' in current_desktop)) and Utility.command_exist('xflock4'):
			return ['xflock4']
		elif desktop_session == 'cinnamon' and Utility.command_exist('cinnamon-screensaver-command'):
			return ['cinnamon-screensaver-command', '--lock']
		elif (desktop_session == 'pantheon' or desktop_session.startswith('lubuntu')) and Utility.command_exist('light-locker-command'):
			return ['light-locker-command', '--lock']
		elif desktop_session == 'mate' and Utility.command_exist('mate-screensaver-command'):
			return ['mate-screensaver-command', '--lock']
		elif desktop_session == 'kde' or 'plasma' in desktop_session or desktop_session.startswith('kubuntu') or os.environ.get('KDE_FULL_SESSION') == 'true':
			return ['qdbus', 'org.freedesktop.ScreenSaver', '/ScreenSaver', 'Lock']
		elif desktop_session in ['gnome', 'unity', 'budgie-desktop'] or desktop_session.startswith('ubuntu'):
			if Utility.command_exist('gnome-screensaver-command'):
				return ['gnome-screensaver-command', '--lock']
			else:
				# From Gnome 3.8 no gnome-screensaver-command
				return ['dbus-send', '--type=method_call', '--dest=org.gnome.ScreenSaver', '/org/gnome/ScreenSaver', 'org.gnome.ScreenSaver.Lock']
		elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
			if 'deprecated' not in os.environ.get('GNOME_DESKTOP_SESSION_ID') and Utility.command_exist('gnome-screensaver-command'):
				# Gnome 2
				return ['gnome-screensaver-command', '--lock']
	return None


def init(ctx, safeeyes_config, plugin_config):
	"""
	Initialize the screensaver plugin.
	"""
	global context
	global lock_screen_command
	global min_seconds
	logging.debug('Initialize Screensaver plugin')
	context = ctx
	min_seconds = plugin_config['min_seconds']
	if plugin_config['command']:
		lock_screen_command = plugin_config['command'].split()
	else:
		lock_screen_command = __lock_screen_command()


def on_start_break(break_obj):
	"""
	Determine the break type and only if it is a long break, enable the lock_screen flag.
	"""
	global lock_screen
	global seconds_passed
	seconds_passed = 0
	if lock_screen_command:
		lock_screen = break_obj.is_long_break()


def on_countdown(countdown, seconds):
	"""
	Keep track of seconds passed from the beginning of long break.
	"""
	global seconds_passed
	seconds_passed = seconds


def on_stop_break():
	"""
	Lock the screen after a long break if the user has not skipped within min_seconds.
	"""
	if lock_screen and seconds_passed >= min_seconds:
		Utility.execute_command(lock_screen_command)
