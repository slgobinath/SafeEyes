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
from Xlib import Xatom, Xutil
from Xlib.display import Display, X
import sys, threading

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkX11

class BreakScreen:
	"""Full screen break window"""

	def __init__(self, on_skip, glade_file, style_sheet_path):
		self.on_skip = on_skip
		self.style_sheet = style_sheet_path
		self.is_pretified = False
		self.key_lock_condition = threading.Condition()

		builder = Gtk.Builder()
		builder.add_from_file(glade_file)
		builder.connect_signals(self)

		self.lbl_message = builder.get_object("lbl_message")
		self.lbl_count = builder.get_object("lbl_count")
		self.btn_skip = builder.get_object("btn_skip")

		self.window = builder.get_object("window_main")
		self.window.stick()
		self.window.set_keep_above(True)
		screen = self.window.get_screen()
		# self.window.resize(screen.get_width(), screen.get_height())

	"""
		Initialize the internal properties from configuration
	"""

	def initialize(self, config):
		self.skip_button_text = config['skip_button_text']
		self.strict_break = config['strict_break']
		self.btn_skip.set_label(self.skip_button_text)
		self.btn_skip.set_visible(not self.strict_break)

	def on_window_delete(self, *args):
		self.lock_keyboard = False
		self.close()

	def on_skip_clicked(self, button):
		self.on_skip()
		self.close()

	def show_count_down(self, count):
		GLib.idle_add(lambda: self.lbl_count.set_text(count))

	def show_message(self, message):
		GLib.idle_add(lambda: self.__show_message(message))

	"""
		Lock the keyboard to prevent the user from using keyboard shortcuts
	"""
	def block_keyboard(self):
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
		display.ungrab_keyboard(X.CurrentTime)
		display.flush()
				
	def release_keyboard(self):
		self.key_lock_condition.acquire()
		self.lock_keyboard = False
		self.key_lock_condition.notify()
		self.key_lock_condition.release()

	def __show_message(self, message):
		self.lbl_message.set_text(message)
		self.window.show_all()
		self.window.present()
		self.window.fullscreen()

		# Set the style only for the first time
		if not self.is_pretified:
			# Set style
			css_provider = Gtk.CssProvider()
			css_provider.load_from_path(self.style_sheet)
			Gtk.StyleContext().add_provider_for_screen(Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
			signal.signal(signal.SIGINT, signal.SIG_DFL)
			self.is_pretified = True

		# If the style is changed, the visibility must be redefined
		self.btn_skip.set_visible(not self.strict_break)
		# Lock the keyboard
		thread = threading.Thread(target=self.block_keyboard)
		thread.start()

	def close(self):
		self.release_keyboard()
		GLib.idle_add(lambda: self.window.hide())
		
