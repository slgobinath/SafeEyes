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

import logging
import os
import threading
import time

import gi
from safeeyes import Utility
from Xlib.display import Display
from Xlib.display import X

gi.require_version('Gtk', '3.0')
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

BREAK_SCREEN_GLADE = os.path.join(Utility.BIN_DIRECTORY, "glade/break_screen.glade")


class BreakScreen(object):
    """
    The fullscreen window which prevents users from using the computer.
    This class reads the break_screen.glade and build the user interface.
    """

    def __init__(self, context, on_skip, on_postpone, style_sheet_path):
        self.context = context
        self.count_labels = []
        self.display = Display()
        self.enable_postpone = False
        self.enable_shortcut = False
        self.is_pretified = False
        self.keycode_shortcut_postpone = 65
        self.keycode_shortcut_skip = 9
        self.on_postpone = on_postpone
        self.on_skip = on_skip
        self.shortcut_disable_time = 2
        self.strict_break = False
        self.windows = []

        # Initialize the theme
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(style_sheet_path)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def initialize(self, config):
        """
        Initialize the internal properties from configuration
        """
        logging.info("Initialize the break screen")
        self.enable_postpone = config.get('allow_postpone', False)
        self.keycode_shortcut_postpone = config.get('shortcut_postpone', 65)
        self.keycode_shortcut_skip = config.get('shortcut_skip', 9)
        self.shortcut_disable_time = config.get('shortcut_disable_time', 2)
        self.strict_break = config.get('strict_break', False)

    def skip_break(self):
        """
        Skip the break from the break screen
        """
        logging.info("User skipped the break")
        # Must call on_skip before close to lock screen before closing the break screen
        self.on_skip()
        self.close()

    def postpone_break(self):
        """
        Postpone the break from the break screen
        """
        logging.info("User postponed the break")
        self.on_postpone()
        self.close()

    def on_window_delete(self, *args):
        """
        Window close event handler.
        """
        logging.info("Closing the break screen")
        self.close()

    def on_skip_clicked(self, button):
        """
        Skip button press event handler.
        """
        self.skip_break()

    def on_postpone_clicked(self, button):
        """
        Postpone button press event handler.
        """
        self.postpone_break()

    def show_count_down(self, countdown, seconds):
        """
        Show/update the count down on all screens.
        """
        self.enable_shortcut = self.shortcut_disable_time <= seconds
        mins, secs = divmod(countdown, 60)
        timeformat = '{:02d}:{:02d}'.format(mins, secs)
        GLib.idle_add(lambda: self.__update_count_down(timeformat))

    def show_message(self, break_obj, widget, tray_actions=[]):
        """
        Show the break screen with the given message on all displays.
        """
        message = break_obj.name
        image_path = break_obj.image
        self.enable_shortcut = self.shortcut_disable_time <= 0
        GLib.idle_add(lambda: self.__show_break_screen(message, image_path, widget, tray_actions))

    def close(self):
        """
        Hide the break screen from active window and destroy all other windows
        """
        logging.info("Close the break screen(s)")
        self.__release_keyboard()

        # Destroy other windows if exists
        GLib.idle_add(lambda: self.__destroy_all_screens())

    def __tray_action(self, button, tray_action):
        """
        Tray action handler.
        Hides all toolbar buttons for this action and call the action provided by the plugin.
        """
        tray_action.reset()
        tray_action.action()

    def __show_break_screen(self, message, image_path, widget, tray_actions):
        """
        Show an empty break screen on all screens.
        """
        # Lock the keyboard
        Utility.start_thread(self.__lock_keyboard)

        screen = Gtk.Window().get_screen()
        no_of_monitors = screen.get_n_monitors()
        logging.info("Show break screens in %d display(s)", no_of_monitors)

        for monitor in range(no_of_monitors):
            monitor_gemoetry = screen.get_monitor_geometry(monitor)
            x = monitor_gemoetry.x
            y = monitor_gemoetry.y

            builder = Gtk.Builder()
            builder.add_from_file(BREAK_SCREEN_GLADE)
            builder.connect_signals(self)

            window = builder.get_object("window_main")
            lbl_message = builder.get_object("lbl_message")
            lbl_count = builder.get_object("lbl_count")
            lbl_widget = builder.get_object("lbl_widget")
            img_break = builder.get_object("img_break")
            box_buttons = builder.get_object("box_buttons")
            toolbar = builder.get_object("toolbar")

            for tray_action in tray_actions:
                toolbar_button = None
                if tray_action.system_icon:
                    toolbar_button = Gtk.ToolButton.new_from_stock(tray_action.get_icon())
                else:
                    toolbar_button = Gtk.ToolButton.new(tray_action.get_icon(), tray_action.name)
                tray_action.add_toolbar_button(toolbar_button)
                toolbar_button.connect("clicked", lambda button, action: self.__tray_action(button, action), tray_action)
                toolbar_button.set_tooltip_text(_(tray_action.name))
                toolbar.add(toolbar_button)
                toolbar_button.show()

            # Add the buttons
            if self.enable_postpone:
                # Add postpone button
                btn_postpone = Gtk.Button(_('Postpone'))
                btn_postpone.get_style_context().add_class('btn_postpone')
                btn_postpone.connect('clicked', self.on_postpone_clicked)
                btn_postpone.set_visible(True)
                box_buttons.pack_start(btn_postpone, True, True, 0)

            if not self.strict_break:
                # Add the skip button
                btn_skip = Gtk.Button(_('Skip'))
                btn_skip.get_style_context().add_class('btn_skip')
                btn_skip.connect('clicked', self.on_skip_clicked)
                btn_skip.set_visible(True)
                box_buttons.pack_start(btn_skip, True, True, 0)

            # Set values
            if image_path:
                img_break.set_from_file(image_path)
            lbl_message.set_label(message)
            lbl_widget.set_markup(widget)

            self.windows.append(window)
            self.count_labels.append(lbl_count)

            # Set visual to apply css theme. It should be called before show method.
            window.set_visual(window.get_screen().get_rgba_visual())
            if self.context['desktop'] == 'kde':
                # Fix flickering screen in KDE by setting opacity to 1
                window.set_opacity(0.9)

            # In Unity, move the window before present
            window.move(x, y)
            window.stick()
            window.set_keep_above(True)
            window.present()
            # In other desktop environments, move the window after present
            # if self.context['desktop'] != 'unity':
            window.move(x, y)
            window.resize(monitor_gemoetry.width, monitor_gemoetry.height)
            logging.info("Moved break screen to Display[%d, %d]", x, y)
            window.fullscreen()

    def __update_count_down(self, count):
        """
        Update the countdown on all break screens.
        """
        for label in self.count_labels:
            label.set_text(count)

    def __lock_keyboard(self):
        """
        Lock the keyboard to prevent the user from using keyboard shortcuts
        """
        logging.info("Lock the keyboard")
        self.lock_keyboard = True

        # Grab the keyboard
        root = self.display.screen().root
        root.change_attributes(event_mask=X.KeyPressMask | X.KeyReleaseMask)
        root.grab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime)

        # Consume keyboard events
        while self.lock_keyboard:
            if self.display.pending_events() > 0:
                # Avoid waiting for next event by checking pending events
                event = self.display.next_event()
                if self.enable_shortcut and event.type == X.KeyPress:
                    if event.detail == self.keycode_shortcut_skip and not self.strict_break:
                        self.skip_break()
                        break
                    elif self.enable_postpone and event.detail == self.keycode_shortcut_postpone:
                        self.postpone_break()
                        break
            else:
                # Reduce the CPU usage by sleeping for a second
                time.sleep(1)

    def __release_keyboard(self):
        """
        Release the locked keyboard.
        """
        logging.info("Unlock the keyboard")
        self.lock_keyboard = False
        self.display.ungrab_keyboard(X.CurrentTime)
        self.display.flush()

    def __destroy_all_screens(self):
        """
        Close all the break screens.
        """
        for win in self.windows:
            win.destroy()
        del self.windows[:]
        del self.count_labels[:]
