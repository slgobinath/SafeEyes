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
"""This module creates the AboutDialog which shows the version and license."""

import os
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from safeeyes import utility
from safeeyes.translations import translate as _

ABOUT_DIALOG_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/about_dialog.glade")


@Gtk.Template(filename=ABOUT_DIALOG_GLADE)
class AboutDialog(Gtk.ApplicationWindow):
    """AboutDialog reads the about_dialog.glade and build the user interface
    using that file.

    It shows the application name with version, a small description,
    license and the GitHub url.
    """

    __gtype_name__ = "AboutDialog"

    lbl_decription: Gtk.Label = Gtk.Template.Child()
    lbl_license: Gtk.Label = Gtk.Template.Child()
    lbl_app_name: Gtk.Label = Gtk.Template.Child()

    def __init__(self, application: Gtk.Application, version: str):
        super().__init__(application=application)

        self.lbl_decription.set_label(
            _(
                "Safe Eyes protects your eyes from eye strain (asthenopia) by reminding"
                " you to take breaks while you're working long hours at the computer"
            )
        )
        self.lbl_license.set_label(_("License") + ":")

        # Set the version at the runtime
        self.lbl_app_name.set_label("Safe Eyes " + version)

    def show(self) -> None:
        """Show the About dialog."""
        self.present()

    @Gtk.Template.Callback()
    def on_window_delete(self, *args) -> None:
        """Window close event handler."""
        self.destroy()

    @Gtk.Template.Callback()
    def on_close_clicked(self, *args) -> None:
        """Close button click event handler."""
        self.destroy()
