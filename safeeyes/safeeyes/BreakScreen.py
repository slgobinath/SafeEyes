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
import signal
import sys
import threading
import logging
from Xlib import Xatom, Xutil
from Xlib.display import Display, X

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkX11

class BreakScreen:
	"""Full screen break window"""

	def __init__(self, on_skip, glade_file, style_sheet_path):
		self.on_skip = on_skip
		self.is_pretified = False
		self.key_lock_condition = threading.Condition()
		self.windows = []
		self.count_labels = []
		self.glade_file = glade_file

		# Initialize the theme
		css_provider = Gtk.CssProvider()
		css_provider.load_from_path(style_sheet_path)
		Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


	"""
		Initialize the internal properties from configuration
	"""
	def initialize(self, config, language):
		logging.info("Initialize the break screen")
		self.skip_button_text = language['ui_controls']['skip']
		self.strict_break = config['strict_break']

	def on_window_delete(self, *args):
		logging.info("Closing the break screen")
		self.lock_keyboard = False
		self.close()

	def on_skip_clicked(self, button):
		logging.info("User skipped the break")
		self.on_skip()
		self.close()

	def show_count_down(self, count):
		GLib.idle_add(lambda: self.__show_count_down(count))

	def __show_count_down(self, count):
		for label in self.count_labels:
			label.set_text(count)

	def show_message(self, message):
		GLib.idle_add(lambda: self.__show_message(message))

	"""
		Lock the keyboard to prevent the user from using keyboard shortcuts
	"""
	def block_keyboard(self):
		logging.info("Lock the keyboard")
		self.lock_keyboard = True
		display = Display()
		root = display.screen().root
		# Grap the keyboard
		root.grab_keyboard(owner_events = False, pointer_mode = X.GrabModeAsync, keyboard_mode = X.GrabModeAsync, time = X.CurrentTime)
		# Consume keyboard events
		self.key_lock_condition.acquire()
		while self.lock_keyboard:
			self.key_lock_condition.wait()
		self.key_lock_condition.release()
		
		# Ungrap the keyboard
		logging.info("Unlock the keyboard")
		display.ungrab_keyboard(X.CurrentTime)
		display.flush()


	"""
		Show an empty break screen on each non-active screens.
	"""
	def show_break_screen(self, message):
		logging.info("Show break screens in all displays")
		screen = Gtk.Window().get_screen()
		no_of_monitors = screen.get_n_monitors()

		for monitor in range(no_of_monitors):
			monitor_gemoetry = screen.get_monitor_geometry(monitor)
			x = monitor_gemoetry.x
			y = monitor_gemoetry.y

			builder = Gtk.Builder()
			builder.add_from_file(self.glade_file)
			builder.connect_signals(self)

			window = builder.get_object("window_main")
			lbl_message = builder.get_object("lbl_message")
			lbl_count = builder.get_object("lbl_count")
			btn_skip = builder.get_object("btn_skip")

			lbl_message.set_label(message)
			btn_skip.set_label(self.skip_button_text)
			btn_skip.set_visible(not self.strict_break)

			self.windows.append(window)
			self.count_labels.append(lbl_count)

			# Set visual to apply css theme. It should be called before show method.
			window.set_visual(window.get_screen().get_rgba_visual())

			window.move(x, y)
			window.stick()
			window.set_keep_above(True)
			window.present()
			window.fullscreen()
			

	def release_keyboard(self):
		self.key_lock_condition.acquire()
		self.lock_keyboard = False
		self.key_lock_condition.notify()
		self.key_lock_condition.release()

	def __show_message(self, message):
		# Lock the keyboard
		thread = threading.Thread(target=self.block_keyboard)
		thread.start()

		self.show_break_screen(message)


	"""
		Hide the break screen from active window and destroy all other windows
	"""
	def close(self):
		logging.info("Close the break screen(s)")
		self.release_keyboard()

		# Destroy other windows if exists
		GLib.idle_add(lambda: self.__close())

	def __close(self):
		for win in self.windows:
			win.destroy()
		del self.windows[:]
		del self.count_labels[:]
