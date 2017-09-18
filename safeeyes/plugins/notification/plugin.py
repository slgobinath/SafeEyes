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
gi.require_version('Notify', '0.7')
from gi.repository import Notify
import logging
from safeeyes.model import BreakType
from safeeyes import Utility

"""
Safe Eyes Notification plugin
"""

APPINDICATOR_ID = 'safeeyes'
notification = None
context = None


def init(ctx, safeeyes_config, plugin_config):
	"""
	Initialize the plugin.
	"""
	global context
	logging.debug('Initialize Notification plugin')
	context = ctx


def on_start():
	"""
	Initialize the native notification.
	"""
	logging.debug('Start Notification plugin')
	Notify.init(APPINDICATOR_ID)


def on_pre_break(break_obj):
	"""
	Show the notification
	"""
	# Construct the message based on the type of the next break
	message = '\n'
	warning_time = 10
	if break_obj.type == BreakType.SHORT_BREAK:
		message += context['language']['messages']['ready_for_a_short_break'].format(warning_time)
	else:
		message += context['language']['messages']['ready_for_a_long_break'].format(warning_time)

	global notification
	notification = Notify.Notification.new('Safe Eyes', message, icon='safeeyes_enabled')
	try:
		notification.show()
	except Exception as e:
		logging.exception('Error in showing notification', e)


def on_start_break(break_obj):
	"""
	Close the notification.
	"""
	logging.info('Close pre-break notification')
	global notification
	if notification:
		try:
			notification.close()
			notification = None
		except Exception:
			# Some Linux systems automatically close the notification.
			pass
		pass


def on_stop():
	"""
	Uninitialize the registered notificaion.
	"""
	logging.debug('Stop Notification plugin')
	Utility.execute_main_thread(Notify.uninit)
