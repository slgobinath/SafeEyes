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

import gi, logging
gi.require_version('Notify', '0.7')
from gi.repository import Notify
from safeeyes import Utility


APPINDICATOR_ID = 'safeeyes'

class Notification:
	"""
		This class is responsible for the notification to the user before the break.
	"""


	def __init__(self, language):
		"""
		Initialize the notification.
		"""
		logging.info('Initialize the notification')
		Notify.init(APPINDICATOR_ID)
		self.language = language


	def show(self, warning_time):
		"""
		Show the notification
		"""
		logging.info('Show pre-break notification')
		self.notification = Notify.Notification.new('Safe Eyes', '\n' + self.language['messages']['ready_for_a_break'].format(warning_time), icon='safeeyes_enabled')
		try:
			self.notification.show()
		except Exception as e:
			logging.exception('Error in showing notification', e)


	def close(self):
		"""
		Close the notification if it is not closed by the system already.
		"""
		logging.info('Close pre-break notification')
		try:
			self.notification.close()
		except:
			# Some Linux systems automatically close the notification.
			pass


	def quite(self):
		"""
		Uninitialize the notification. Call this method when closing the application.
		"""
		logging.info('Uninitialize Safe Eyes notification')
		Utility.execute_main_thread(Notify.uninit)