# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2017  Gobinath

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

import datetime
from typing import Dict, Optional

import gi

from safeeyes.context import Context
from safeeyes.spi.api import Condition
from safeeyes.spi.breaks import BreakType
from safeeyes.thread import worker, main
from safeeyes.util.locale import _

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Gtk
import logging
from safeeyes import utility
import threading
import time

"""
Safe Eyes tray icon plugin
"""

APPINDICATOR_ID = "safeeyes_2"


class TrayIcon:
    """
    Create and show the tray icon along with the tray menu.
    """

    def __init__(self, ctx: Context, plugin_config: Dict):
        self.__context: Context = ctx
        self.__config: dict = plugin_config
        self.__date_time: Optional[datetime.datetime] = None
        self.__active: bool = True
        self.__wakeup_time: Optional[datetime.datetime] = None
        self.__idle_condition: Condition = ctx.thread_api.new_condition()
        self.__lock = threading.Lock()
        self.__allow_disabling: bool = plugin_config["allow_disabling"]
        self.__animate: bool = False

        # Construct the tray icon
        self.__indicator = appindicator.Indicator.new(
            APPINDICATOR_ID, "safeeyes_enabled", appindicator.IndicatorCategory.APPLICATION_STATUS)
        self.__indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

        # Construct the context menu
        self.__menu = Gtk.Menu()
        self.__item_info = Gtk.ImageMenuItem()
        self.__item_separator = Gtk.SeparatorMenuItem()
        self.__item_enable = Gtk.MenuItem()
        self.__item_disable = Gtk.MenuItem()
        self.__sub_menu_item_until_restart = Gtk.MenuItem()
        self.__item_settings = Gtk.MenuItem()
        self.__item_about = Gtk.MenuItem()
        self.__item_quit = Gtk.MenuItem()
        self.__item_manual_break = Gtk.MenuItem()
        self.__sub_menu_manual_next_break = Gtk.MenuItem()
        self.__sub_menu_manual_next_short_break = Gtk.MenuItem()
        self.__sub_menu_manual_next_long_break = Gtk.MenuItem()
        self.__sub_menu_disable = Gtk.Menu()
        self.__sub_menu_manual_break = Gtk.Menu()

        # Next break info menu item
        img_timer = Gtk.Image()
        img_timer.set_from_icon_name("safeeyes_timer", 16)
        self.__item_info.set_image(img_timer)

        self.__sub_menu_disable_items = []

        # Read disable options and build the sub menu
        for disable_option in plugin_config["disable_options"]:
            time_in_minutes = disable_option["time"]
            label = []
            # Validate time value
            if not isinstance(time_in_minutes, int) or time_in_minutes <= 0:
                logging.error("Invalid time in disable option: " + str(time_in_minutes))
                continue
            time_unit = disable_option["unit"].lower()
            if time_unit == "seconds" or time_unit == "second":
                time_in_minutes = int(time_in_minutes / 60)
                label = ["For %d Second", "For %d Seconds"]
            elif time_unit == "minutes" or time_unit == "minute":
                time_in_minutes = int(time_in_minutes * 1)
                label = ["For %d Minute", "For %d Minutes"]
            elif time_unit == "hours" or time_unit == "hour":
                time_in_minutes = int(time_in_minutes * 60)
                label = ["For %d Hour", "For %d Hours"]
            else:
                # Invalid unit
                logging.error("Invalid unit in disable option: " + str(disable_option))
                continue

            # Create submenu
            sub_menu_item = Gtk.MenuItem()
            sub_menu_item.connect("activate", self.__on_disable_clicked, time_in_minutes)
            self.__sub_menu_disable_items.append([sub_menu_item, label, disable_option["time"]])
            self.__sub_menu_disable.append(sub_menu_item)

        self.__sub_menu_disable.append(self.__sub_menu_item_until_restart)
        self.__item_disable.set_submenu(self.__sub_menu_disable)
        self.__sub_menu_manual_break.append(self.__sub_menu_manual_next_break)
        self.__sub_menu_manual_break.append(self.__sub_menu_manual_next_short_break)
        self.__sub_menu_manual_break.append(self.__sub_menu_manual_next_long_break)
        self.__item_manual_break.set_submenu(self.__sub_menu_manual_break)

        self.__sub_menu_item_until_restart.connect("activate", self.__on_disable_clicked, -1)
        self.__sub_menu_manual_next_break.connect("activate", self.__on_manual_break_clicked, None)
        self.__sub_menu_manual_next_short_break.connect("activate", self.__on_manual_break_clicked, BreakType.SHORT)
        self.__sub_menu_manual_next_long_break.connect("activate", self.__on_manual_break_clicked, BreakType.LONG)
        self.__item_enable.connect("activate", self.__on_enable_clicked)
        self.__item_settings.connect("activate", self.__on_show_settings)
        self.__item_about.connect("activate", self.__on_show_about)
        self.__item_quit.connect("activate", self.__on_quit_safe_eyes)

        self.__set_labels()

        # At startup, no need to activate the menu
        self.__item_enable.set_sensitive(False)

        # Append all menu items and show the menu
        self.__menu.append(self.__item_info)
        self.__menu.append(self.__item_separator)
        self.__menu.append(self.__item_enable)
        self.__menu.append(self.__item_disable)
        self.__menu.append(self.__item_manual_break)
        self.__menu.append(self.__item_settings)
        self.__menu.append(self.__item_about)
        self.__menu.append(self.__item_quit)
        self.__menu.show_all()

        self.__set_visibility()

        self.__indicator.set_menu(self.__menu)

    def initialize(self, plugin_config):
        """
        Initialize the tray icon by setting the config.
        """
        self.__config = plugin_config
        self.__set_labels()
        self.__allow_disabling = plugin_config["allow_disabling"]
        self.__set_visibility()

    @main
    def __set_visibility(self) -> None:
        self.__item_enable.set_visible(self.__allow_disabling)
        self.__item_disable.set_visible(self.__allow_disabling)
        self.__item_quit.set_visible(self.__allow_disabling)
        self.__item_quit.set_visible(self.__allow_disabling)

    @main
    def __set_labels(self):
        """
        Update the text of menu items based on the selected language.
        """
        for entry in self.__sub_menu_disable_items:
            entry[0].set_label(self.__context.locale.ngettext(entry[1][0], entry[1][1], entry[2]) % entry[2])

        self.__sub_menu_item_until_restart.set_label(_("Until restart"))
        self.__item_enable.set_label(_("Enable Safe Eyes"))
        self.__item_disable.set_label(_("Disable Safe Eyes"))

        breaks_found = self.__context.break_api.has_breaks()
        if breaks_found:
            if self.__active:
                if self.__date_time:
                    self.__set_next_break_info()
                self.__indicator.set_icon("safeeyes_enabled")
            else:
                if self.__wakeup_time:
                    self.__item_info.set_label(_("Disabled until %s") % utility.format_time(self.__wakeup_time))
                else:
                    self.__item_info.set_label(_("Disabled until restart"))
                self.__indicator.set_label("", "")
                self.__indicator.set_icon("safeeyes_disabled")
        else:
            self.__item_info.set_label(_("No Breaks Available"))
            self.__indicator.set_label("", "")
            self.__indicator.set_icon("safeeyes_disabled")
        self.__item_info.set_sensitive(breaks_found and self.__active)
        self.__item_enable.set_sensitive(breaks_found and not self.__active)
        self.__item_disable.set_sensitive(breaks_found and self.__active)
        self.__item_manual_break.set_sensitive(breaks_found and self.__active)

        self.__item_manual_break.set_label(_("Take a break now"))
        self.__sub_menu_manual_next_break.set_label(_("Any break"))
        self.__sub_menu_manual_next_short_break.set_label(_("Short break"))
        self.__sub_menu_manual_next_long_break.set_label(_("Long break"))
        self.__item_settings.set_label(_("Settings"))
        self.__item_about.set_label(_("About"))
        self.__item_quit.set_label(_("Quit"))

    def __on_quit_safe_eyes(self, *args):
        """
        Handle Quit menu action.
        This action terminates the application.
        """
        with self.__lock:
            self.__active = True
            # Notify all schedulers
            self.__idle_condition.release_all()
        self.__context.core_api.quit()

    def __on_show_settings(self, *args):
        """
        Handle Settings menu action.
        This action shows the Settings dialog.
        """
        self.__context.window_api.show_settings()

    def __on_show_about(self, *args):
        """
        Handle About menu action.
        This action shows the About dialog.
        """
        self.__context.window_api.show_about()

    def __on_manual_break_clicked(self, *args):
        """
        Trigger a break manually.
        """
        if len(args) > 1:
            break_type = args[1]
            self.__context.break_api.take_break(break_type)
        else:
            self.__context.break_api.take_break()

    def __on_enable_clicked(self, *args):
        """
        Handle "Enable Safe Eyes" menu action.
        This action enables the application if it is currently disabled.
        """
        # active = self.item_enable.get_active()
        if not self.__active:
            with self.__lock:
                self.enable_ui()
                self.__context.core_api.start()
                # Notify all schedulers
                self.__idle_condition.release_all()

    def __on_disable_clicked(self, *args):
        """
        Handle the menu actions of all the sub menus of "Disable Safe Eyes".
        This action disables the application if it is currently active.
        """
        # active = self.item_enable.get_active()
        if self.__active and len(args) > 1:
            self.disable_ui()

            time_to_wait = args[1]
            if time_to_wait <= 0:
                info = _("Disabled until restart")
                self.__context.core_api.stop(info)
                self.__wakeup_time = None
                self.__item_info.set_label(info)
            else:
                self.__wakeup_time = datetime.datetime.now() + datetime.timedelta(minutes=time_to_wait)
                info = _("Disabled until %s") % utility.format_time(self.__wakeup_time)
                self.__context.core_api.set_status(info)
                self.__context.core_api.stop()
                self.__item_info.set_label(info)
                self.__schedule_resume(time_to_wait)

    def update_next_break_time(self, date_time: datetime.datetime):
        """
        Update the next break time to be displayed in the menu and optionally in the tray icon.
        """
        self.__date_time = date_time
        self.__set_next_break_info()

    @main
    def __set_next_break_info(self):
        """
        A private method to be called within this class to update the next break information using self.dateTime.
        """
        formatted_time = utility.format_time(self.__date_time)
        message = _("Next break at %s") % formatted_time
        # Update the menu item label
        self.__set_label(message)
        # Update the tray icon label
        if self.__config.get("show_time_in_tray", False):
            self.__indicator.set_label(formatted_time, "")
        else:
            self.__indicator.set_label("", "")

    @main
    def lock_menu(self):
        """
        This method is called by the core to prevent user from disabling Safe Eyes after the notification.
        """
        if self.__active:
            self.__menu.set_sensitive(False)

    @main
    def unlock_menu(self):
        """
        This method is called by the core to activate the menu after the the break.
        """
        if self.__active:
            self.__menu.set_sensitive(True)

    @main
    def disable_ui(self):
        """
        Change the UI to disabled state.
        """
        if self.__active:
            logging.debug("Tray Icon: disable the icon")
            self.__active = False
            self.__indicator.set_icon("safeeyes_disabled")
            self.__item_info.set_label(_("Disabled until restart"))
            self.__indicator.set_label("", "")
            self.__item_info.set_sensitive(False)
            self.__item_enable.set_sensitive(True)
            self.__item_disable.set_sensitive(False)
            self.__item_manual_break.set_sensitive(False)

    @main
    def enable_ui(self):
        """
        Change the UI to enabled state.
        """
        if not self.__active:
            logging.debug("Tray Icon: enable the icon")
            self.__active = True
            self.__indicator.set_icon("safeeyes_enabled")
            self.__item_info.set_sensitive(True)
            self.__item_enable.set_sensitive(False)
            self.__item_disable.set_sensitive(True)
            self.__item_manual_break.set_sensitive(True)

    @worker
    def __schedule_resume(self, time_minutes):
        """
        Schedule a local timer to enable Safe Eyes after the given timeout.
        """
        self.__idle_condition.hold(time_minutes * 60)

        with self.__lock:
            if not self.__active:
                self.__activate_enable_menu()

    @worker
    def start_animation(self):
        while self.__active and self.__animate:
            time.sleep(0.5)
            self.__set_icon("safeeyes_disabled")
            time.sleep(0.5)
            self.__set_icon("safeeyes_enabled")

    def stop_animation(self):
        self.__animate = False
        if self.__active:
            self.__set_icon("safeeyes_enabled")
        else:
            self.__set_icon("safeeyes_disabled")

    @main
    def __set_icon(self, icon_name: str) -> None:
        self.__indicator.set_icon(icon_name)

    @main
    def __activate_enable_menu(self) -> None:
        self.__item_enable.activate()

    @main
    def __set_label(self, message: str) -> None:
        self.__item_info.set_label(message)


context: Context
tray_icon: TrayIcon = None


def init(ctx: Context, plugin_config: dict):
    """
    Initialize the tray icon.
    """
    global context
    global tray_icon
    context = ctx
    if not tray_icon:
        tray_icon = TrayIcon(context, plugin_config)
    else:
        tray_icon.initialize(plugin_config)


def update_next_break(break_obj, next_short_break_time: Optional[datetime.datetime],
                      next_long_break_time: Optional[datetime.datetime]):
    """
    Update the next break time.
    """
    next_break_time: Optional[datetime.datetime] = None
    if next_short_break_time is not None:
        next_break_time = next_short_break_time if next_long_break_time is None or next_short_break_time < next_long_break_time else next_long_break_time
    elif next_long_break_time is not None:
        next_break_time = next_long_break_time if next_short_break_time is None or next_long_break_time < next_short_break_time else next_short_break_time

    if next_break_time:
        tray_icon.update_next_break_time(next_break_time)


def on_pre_break(break_obj):
    """
    Disable the menu if strict_break is enabled
    """
    if context.config.get("strict_break"):
        tray_icon.lock_menu()
    tray_icon.__animate = True
    tray_icon.start_animation()


def on_start_break(break_obj):
    tray_icon.stop_animation()


def on_stop_break():
    tray_icon.unlock_menu()


def on_start():
    """
    Enable the tray icon.
    """
    tray_icon.enable_ui()


def on_stop():
    """
    Disable the tray icon.
    """
    tray_icon.disable_ui()
