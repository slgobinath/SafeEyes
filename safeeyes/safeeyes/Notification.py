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

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, Gdk, GLib, GdkX11
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Notify
APPINDICATOR_ID = 'safeeyes'

class Notification:
	def __init__(self):
		Notify.init(APPINDICATOR_ID)
		# self.notification.set_timeout(500)

	def show(self, warning_time):
		# self.notification.show()
		# self.notification.close()
		self.notification = Notify.Notification.new("Safe Eyes", "\nReady for a break in " + str(warning_time) + " seconds.", icon="safeeyes_enabled")
		# GLib.idle_add(lambda: self.notification.show())
		self.notification.show()

	def close(self):
		try:
			self.notification.close()
		except:
			pass
		# GLib.idle_add(lambda: self.notification.close())

	def quite(self):
		# Notify.uninit()
		GLib.idle_add(lambda: Notify.uninit())

# notification = Notification()
# notification.show(10)
# Gtk.main()