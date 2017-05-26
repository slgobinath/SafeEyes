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

import gi, signal, sys, threading, logging
from Xlib import Xatom, Xutil
from Xlib.display import Display, X
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkX11


"""
	The fullscreen window which prevents users from using the computer.
"""
class BreakScreen:

	"""
		Read the break_screen.glade and build the user interface.
	"""
	def __init__(self, on_skip, on_postpone, glade_file, style_sheet_path):
		self.on_skip = on_skip
		self.on_postpone = on_postpone
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
		self.postpone_button_text = language['ui_controls']['postpone']
		self.strict_break = config.get('strict_break', False)
		self.enable_postpone = config.get('allow_postpone', False)


	"""
		Window close event handler.
	"""
	def on_window_delete(self, *args):
		logging.info("Closing the break screen")
		self.lock_keyboard = False
		self.close()


	"""
		Skip button press event handler.
	"""
	def on_skip_clicked(self, button):
		logging.info("User skipped the break")
		# Must call on_skip before close to lock screen before closing the break screen
		self.on_skip()
		self.close()


	"""
		Postpone button press event handler.
	"""
	def on_postpone_clicked(self, button):
		logging.info("User postponed the break")
		self.on_postpone()
		self.close()


	"""
		Show/update the count down on all screens.
	"""
	def show_count_down(self, count):
		GLib.idle_add(lambda: self.__update_count_down(count))


	"""
		Show the break screen with the given message on all displays.
	"""
	def show_message(self, message, image_path, plugins_data):
		GLib.idle_add(lambda: self.__show_break_screen(message, image_path, plugins_data))


	"""
		Hide the break screen from active window and destroy all other windows
	"""
	def close(self):
		logging.info("Close the break screen(s)")
		self.__release_keyboard()

		# Destroy other windows if exists
		GLib.idle_add(lambda: self.__destroy_all_screens())


	"""
		Show an empty break screen on all screens.
	"""
	def __show_break_screen(self, message, image_path, plugins_data):
		# Lock the keyboard
		thread = threading.Thread(target=self.__lock_keyboard)
		thread.start()

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
			lbl_left = builder.get_object("lbl_left")
			lbl_right = builder.get_object("lbl_right")
			img_break = builder.get_object("img_break")
			box_buttons = builder.get_object("box_buttons")

			# Add the buttons
			if not self.strict_break:
				# Add postpone button
				if self.enable_postpone:
					btn_postpone = Gtk.Button(self.postpone_button_text)
					btn_postpone.get_style_context().add_class('btn_postpone')
					btn_postpone.connect('clicked', self.on_postpone_clicked)
					btn_postpone.set_visible(True)
					box_buttons.pack_start(btn_postpone, True, True, 0)

				# Add the skip button
				btn_skip = Gtk.Button(self.skip_button_text)
				btn_skip.get_style_context().add_class('btn_skip')
				btn_skip.connect('clicked', self.on_skip_clicked)
				btn_skip.set_visible(True)
				box_buttons.pack_start(btn_skip, True, True, 0)



			# Set values
			if image_path:
				img_break.set_from_file(image_path)
			lbl_message.set_label(message)
			lbl_left.set_markup(plugins_data['left']);
			lbl_right.set_markup(plugins_data['right']);

			self.windows.append(window)
			self.count_labels.append(lbl_count)

			# Set visual to apply css theme. It should be called before show method.
			window.set_visual(window.get_screen().get_rgba_visual())

			window.move(x, y)
			window.stick()
			window.set_keep_above(True)
			window.present()
			window.fullscreen()


	"""
		Update the countdown on all break screens.
	"""
	def __update_count_down(self, count):
		for label in self.count_labels:
			label.set_text(count)


	"""
		Lock the keyboard to prevent the user from using keyboard shortcuts
	"""
	def __lock_keyboard(self):
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
		Release the locked keyboard.
	"""
	def __release_keyboard(self):
		self.key_lock_condition.acquire()
		self.lock_keyboard = False
		self.key_lock_condition.notify()
		self.key_lock_condition.release()


	"""
		Close all the break screens.
	"""
	def __destroy_all_screens(self):
		for win in self.windows:
			win.destroy()
		del self.windows[:]
		del self.count_labels[:]
