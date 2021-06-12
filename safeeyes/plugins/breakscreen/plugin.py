# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2021  Gobinath

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
from typing import List

import gi
from Xlib.display import Display

from safeeyes import utility
from safeeyes.context import Context
from safeeyes.spi.breaks import Break
from safeeyes.spi.plugin import TrayAction
from safeeyes.thread import main, worker

gi.require_version('Gtk', '3.0')
from gi.repository import Gdk
from gi.repository import Gtk

BREAK_SCREEN_GLADE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "break_screen.glade")


class BreakScreen:
    """
    The fullscreen window which prevents users from using the computer.
    This class reads the break_screen.glade and build the user interface.
    """

    def __init__(self, context: Context, config: dict, style_sheet_path):
        self.__context: Context = context
        self.__count_labels: List[Gtk.Label] = []
        self.__display: Display = Display()
        self.__allow_skipping: bool = config.get('allow_skipping', True)
        self.__allow_postponing: bool = config.get('allow_postponing', False)
        self.__postpone_duration: int = config.get('postpone_duration', 5) * 60
        self.__keycode_shortcut_skip: int = config.get('skip_keyboard_shortcut', 9)
        self.__keycode_shortcut_postpone: int = config.get('postpone_keyboard_shortcut', 65)
        self.__shortcut_disable_time: int = config.get('keyboard_disabled_period', 2)
        self.__enable_shortcut: bool = False
        self.__keyboard_locked: bool = False
        self.__windows: List[Gtk.Window] = []

        # Initialize the theme
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(style_sheet_path)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css_provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def skip_break(self):
        """
        Skip the break from the break screen
        """
        logging.info("User skipped the break")
        # Must call on_skip before close to lock screen before closing the break screen
        self.__context.break_api.skip()
        self.close()

    def postpone_break(self):
        """
        Postpone the break from the break screen
        """
        logging.info("User postponed the break")
        self.__context.break_api.postpone(self.__postpone_duration)
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
        self.__enable_shortcut = 0 <= self.__shortcut_disable_time <= seconds
        minutes, secs = divmod(countdown, 60)
        time_format = '{:02d}:{:02d}'.format(minutes, secs)
        self.__update_count_down(time_format)

    def show_message(self, break_obj):
        """
        Show the break screen with the given message on all displays.
        """
        self.__enable_shortcut = self.__shortcut_disable_time == 0

        message = break_obj.name
        image_path = break_obj.image
        widget = self.__get_widgets(break_obj)
        tray_actions = self.__context.plugin_api.get_tray_actions(break_obj)
        self.__show_break_screen(message, image_path, widget, tray_actions)

    def close(self):
        """
        Hide the break screen from active window and destroy all other windows
        """
        logging.info("Close the break screen(s)")
        self.__release_keyboard()

        # Destroy other windows if exists
        self.__destroy_all_screens()

    @staticmethod
    def __tray_action(button, tray_action: TrayAction):
        """
        Tray action handler.
        Hides all toolbar buttons for this action and call the action provided by the plugin.
        """
        tray_action.reset()
        tray_action.action()

    @main
    def __show_break_screen(self, message, image_path, widget, tray_actions):
        """
        Show an empty break screen on all screens.
        """
        # Lock the keyboard
        self.__lock_keyboard()

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

            window: Gtk.Window = builder.get_object("window_main")
            window.set_title("SafeEyes-" + str(monitor))
            lbl_message = builder.get_object("lbl_message")
            lbl_count: Gtk.Label = builder.get_object("lbl_count")
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
                toolbar_button.connect("clicked", lambda button, action: BreakScreen.__tray_action(button, action),
                                       tray_action)
                toolbar_button.set_tooltip_text(_(tray_action.name))
                toolbar.add(toolbar_button)
                toolbar_button.show()

            # Add the buttons
            if self.__allow_postponing:
                # Add postpone button
                btn_postpone = Gtk.Button(_('Postpone'))
                btn_postpone.get_style_context().add_class('btn_postpone')
                btn_postpone.connect('clicked', self.on_postpone_clicked)
                btn_postpone.set_visible(True)
                box_buttons.pack_start(btn_postpone, True, True, 0)

            if self.__allow_skipping:
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

            self.__windows.append(window)
            self.__count_labels.append(lbl_count)

            # Set visual to apply css theme. It should be called before show method.
            window.set_visual(window.get_screen().get_rgba_visual())
            if self.__context.env.name == 'kde':
                # Fix flickering screen in KDE by setting opacity to 1
                window.set_opacity(0.9)

            # In Unity, move the window before present
            window.move(x, y)
            window.resize(monitor_gemoetry.width, monitor_gemoetry.height)
            window.stick()
            window.set_keep_above(True)
            window.fullscreen()
            window.present()
            # In other desktop environments, move the window after present
            window.move(x, y)
            window.resize(monitor_gemoetry.width, monitor_gemoetry.height)
            logging.info("Moved break screen to Display[%d, %d]", x, y)

    @main
    def __update_count_down(self, count):
        """
        Update the countdown on all break screens.
        """
        for label in self.__count_labels:
            label.set_text(count)

    @worker
    def __lock_keyboard(self):
        """
        Lock the keyboard to prevent the user from using keyboard shortcuts
        """
        logging.info("Lock the keyboard")
        self.__keyboard_locked = True

        # # Grab the keyboard
        # root = self.__display.screen().root
        # root.change_attributes(event_mask=X.KeyPressMask | X.KeyReleaseMask)
        # root.grab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime)
        #
        # # Consume keyboard events
        # while self.__keyboard_locked:
        #     if self.__display.pending_events() > 0:
        #         # Avoid waiting for next event by checking pending events
        #         event = self.__display.next_event()
        #         if self.__enable_shortcut and event.type == X.KeyPress:
        #             if self.__allow_skipping and event.detail == self.__keycode_shortcut_skip:
        #                 self.skip_break()
        #                 break
        #             elif self.__allow_postponing and event.detail == self.__keycode_shortcut_postpone:
        #                 self.postpone_break()
        #                 break
        #     else:
        #         # Reduce the CPU usage by sleeping for a second
        #         time.sleep(1)

    def __release_keyboard(self):
        """
        Release the locked keyboard.
        """
        logging.info("Break Screen: unlock the keyboard")
        self.__keyboard_locked = False
        # self.__display.ungrab_keyboard(X.CurrentTime)
        # self.__display.flush()

    @main
    def __destroy_all_screens(self):
        """
        Close all the break screens.
        """
        for win in self.__windows:
            win.destroy()
        del self.__windows[:]
        del self.__count_labels[:]

    def __get_widgets(self, break_obj: Break) -> str:
        widget_html = ''
        for widget in self.__context.plugin_api.get_widgets(break_obj):
            if widget is not None and not widget.is_empty():
                widget_html += widget.format()
        return widget_html.strip()


safe_eyes_context: Context
break_screen: BreakScreen
break_config: dict


def init(context: Context, config: dict) -> None:
    """
    This function is called to initialize the plugin.
    """
    logging.info('Break Screen: initialize the plugin')
    global safe_eyes_context, break_config
    safe_eyes_context = context
    break_config = config


def on_start_break(break_obj: Break) -> None:
    """
    Called when starting a break.
    """
    global break_screen
    break_screen = BreakScreen(safe_eyes_context, break_config, utility.STYLE_SHEET_PATH)
    break_screen.show_message(break_obj)


def on_count_down(break_obj: Break, countdown: int, seconds: int) -> None:
    """
    Called during a break.
    """
    if break_screen:
        break_screen.show_count_down(countdown, seconds)


def on_stop_break(break_obj: Break, skipped: bool, postponed: bool) -> None:
    """
    Called when a break is stopped.
    """
    global break_screen
    if break_screen:
        break_screen.close()
    break_screen = None
