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
import logging
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, Gdk, GLib, GdkX11
from gi.repository import AppIndicator3 as appindicator

# Global variables
active = True
APPINDICATOR_ID = 'safeeyes'

class TrayIcon:
	def __init__(self, language, on_show_settings, on_enable, on_disable, on_quite):
		logging.info("Initialize the tray icon")
		self.on_show_settings = on_show_settings;
		self.on_quite = on_quite
		self.on_enable = on_enable
		self.on_disable = on_disable
		self.language = language

		# Construct the tray icon
		self.indicator = appindicator.Indicator.new(APPINDICATOR_ID, "safeeyes_enabled", appindicator.IndicatorCategory.APPLICATION_STATUS)
		self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

		# Construct the context menu
		self.menu = Gtk.Menu()


		self.item_info = Gtk.ImageMenuItem('Next break at 10.30 AM')
		img_timer = Gtk.Image()
		img_timer.set_from_icon_name("safeeyes_timer", 16)
		self.item_info.set_image(img_timer)

		self.item_separator = Gtk.SeparatorMenuItem()

		self.item_enable = Gtk.CheckMenuItem(self.language['ui_controls']['enable'])
		self.item_enable.set_active(True)
		self.item_enable.connect('activate', self.on_toogle_enable)

		item_settings = Gtk.MenuItem(self.language['ui_controls']['settings'])
		item_settings.connect('activate', self.show_settings)

		item_quit = Gtk.MenuItem(self.language['ui_controls']['quit'])
		item_quit.connect('activate', self.quit_safe_eyes)

		self.menu.append(self.item_info)
		self.menu.append(self.item_separator)
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

	def next_break_time(self, dateTime):
		logging.info("Update next break information")
		timeStr = dateTime.strftime("%l:%M")
		if dateTime.hour == 12:
			message = self.language['messages']['next_break_at_noon'].format(timeStr)
		elif dateTime.hour < 12:
			message = self.language['messages']['next_break_at_am'].format(timeStr)
		else:
			message = self.language['messages']['next_break_at_pm'].format(timeStr)

		GLib.idle_add(lambda: self.item_info.set_label(message))

	def on_toogle_enable(self, *args):
		active = self.item_enable.get_active()
		if active:
			logging.info("Enable Safe Eyes")
			self.indicator.set_icon("safeeyes_enabled")
			self.item_info.set_sensitive(True)
			self.on_enable()
		else:
			logging.info("Disable Safe Eyes")
			self.indicator.set_icon("safeeyes_disabled")
			self.item_info.set_label(self.language['messages']['safe_eyes_is_disabled'])
			self.item_info.set_sensitive(False)
			self.on_disable()
