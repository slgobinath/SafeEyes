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
from gi.repository import Gtk, Gdk, GLib
from gi.repository import AppIndicator3 as appindicator

# Global variables
active = True
APPINDICATOR_ID = 'safeeyes'

class TrayIcon:
	def __init__(self, on_show_settings, on_enable, on_disable, on_quite):
		self.on_show_settings = on_show_settings;
		self.on_quite = on_quite
		self.on_enable = on_enable
		self.on_disable = on_disable

		# Construct the tray icon
		self.indicator = appindicator.Indicator.new(APPINDICATOR_ID, "safeeyes_enabled", appindicator.IndicatorCategory.APPLICATION_STATUS)
		self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

		# Construct the context menu
		self.menu = Gtk.Menu()

		self.item_enable = Gtk.CheckMenuItem('Enable SafeEyes')
		self.item_enable.set_active(True)
		self.item_enable.connect('activate', self.on_toogle_enable)

		item_settings = Gtk.MenuItem('Settings')
		item_settings.connect('activate', self.show_settings)

		item_quit = Gtk.MenuItem('Quit')
		item_quit.connect('activate', self.quit_safe_eyes)

		self.menu.append(self.item_enable)
		self.menu.append(item_settings)
		self.menu.append(item_quit)
		self.menu.show_all()

		self.indicator.set_menu(self.menu)

	def show_icon(self):
		GLib.idle_add(lambda: self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE))

	def hide_icon(self):
		GLib.idle_add(lambda: self.indicator.set_status(appindicator.IndicatorStatus.PASSIVE))

	def quit_safe_eyes(self, *args):
		self.on_quite()

	def show_settings(self, *args):
		self.on_show_settings()

	def on_toogle_enable(self, *args):
		active = self.item_enable.get_active()
		if active:
			# resume_eyesafe()
			self.indicator.set_icon("safeeyes_enabled")
			self.on_enable()
		else:
			# pause_eyesafe()
			self.indicator.set_icon("safeeyes_disabled")
			self.on_disable()
