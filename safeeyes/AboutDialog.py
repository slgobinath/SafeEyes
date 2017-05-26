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
from gi.repository import Gtk, Gdk, GdkX11


"""
	AboutDialog reads the about_dialog.glade and build the user interface using that file.
	It shows the application name with version, a small description, license and the GitHub url.
"""
class AboutDialog:

	"""
		Read the about_dialog.glade and build the user interface.
	"""
	def __init__(self, glade_file, version, language):
		builder = Gtk.Builder()
		builder.add_from_file(glade_file)
		builder.connect_signals(self)
		self.window = builder.get_object("window_about")
		builder.get_object('lbl_decription').set_label(language['app_info']['description'])
		builder.get_object('lbl_license').set_label(str(language['ui_controls']['license']) + ':')
		builder.get_object('btn_close').set_label(language['ui_controls']['close'])

		# Set the version at the runtime
		builder.get_object("lbl_app_name").set_label("Safe Eyes " + version)


	"""
		Show the About dialog.
	"""
	def show(self):
		self.window.show_all()


	"""
		Window close event handler.
	"""
	def on_window_delete(self, *args):
		self.window.destroy()


	"""
		Close button click event handler.
	"""
	def on_close_clicked(self, button):
		self.window.destroy()
