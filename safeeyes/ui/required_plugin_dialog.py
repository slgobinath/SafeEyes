#!/usr/bin/env python
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
"""
This module creates the RequiredPluginDialog which shows the error for a required plugin.
"""

import os

from safeeyes import utility

REQUIRED_PLUGIN_DIALOG_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/required_plugin_dialog.glade")


class RequiredPluginDialog:
    """
    RequiredPluginDialog shows an error when a plugin has required dependencies.
    """

    def __init__(self, plugin_id, plugin_name, message, on_quit, on_disable_plugin):
        self.on_quit = on_quit
        self.on_disable_plugin = on_disable_plugin

        builder = utility.create_gtk_builder(REQUIRED_PLUGIN_DIALOG_GLADE)
        self.window = builder.get_object('window_required_plugin')

        self.window.connect("delete-event", self.on_window_delete)
        builder.get_object('btn_close').connect('clicked', self.on_close_clicked)
        builder.get_object('btn_disable_plugin').connect('clicked', self.on_disable_plugin_clicked)

        builder.get_object('lbl_header').set_label(_("The required plugin '%s' is missing dependencies!") % _(plugin_name))

        builder.get_object('lbl_main').set_label(_("Please install the dependencies or disable the plugin."))

        builder.get_object('lbl_message').set_label(message)

    def show(self):
        """
        Show the dialog.
        """
        self.window.show_all()

    def on_window_delete(self, *args):
        """
        Window close event handler.
        """
        self.window.destroy()
        self.on_quit()

    def on_close_clicked(self, *args):
        self.window.destroy()
        self.on_quit()

    def on_disable_plugin_clicked(self, *args):
        self.window.destroy()
        self.on_disable_plugin()
