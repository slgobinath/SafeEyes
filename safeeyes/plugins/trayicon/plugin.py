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
import gi
gi.require_version('Gtk', '3.0')
try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3 as appindicator
except:
    #fall back to Ayatana
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as appindicator
from gi.repository import Gtk
import logging
from safeeyes import utility
import threading
import time

"""
Safe Eyes tray icon plugin
"""

APPINDICATOR_ID = 'safeeyes_2'
context = None
tray_icon = None
safeeyes_config = None


class TrayIcon:
    """
    Create and show the tray icon along with the tray menu.
    """

    def __init__(self, context, plugin_config):
        self.context = context
        self.on_show_settings = context['api']['show_settings']
        self.on_show_about = context['api']['show_about']
        self.quit = context['api']['quit']
        self.on_enable = context['api']['enable_safeeyes']
        self.on_disable = context['api']['disable_safeeyes']
        self.take_break = context['api']['take_break']
        self.has_breaks = context['api']['has_breaks']
        self.plugin_config = plugin_config
        self.date_time = None
        self.active = True
        self.wakeup_time = None
        self.idle_condition = threading.Condition()
        self.lock = threading.Lock()
        self.allow_disabling = plugin_config['allow_disabling']
        self.animate = False

        # Construct the tray icon
        self.indicator = appindicator.Indicator.new(
            APPINDICATOR_ID, "safeeyes_enabled", appindicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

        # Construct the context menu
        self.menu = Gtk.Menu()

        # Next break info menu item
        self.item_info = Gtk.ImageMenuItem()
        img_timer = Gtk.Image()
        img_timer.set_from_icon_name("safeeyes_timer", 16)
        self.item_info.set_image(img_timer)

        self.item_separator = Gtk.SeparatorMenuItem()

        self.item_enable = Gtk.MenuItem()
        self.item_enable.connect('activate', self.on_enable_clicked)

        self.item_disable = Gtk.MenuItem()
        self.item_disable.connect('activate', self.on_disable_clicked)

        self.sub_menu_disable = Gtk.Menu()
        self.sub_menu_items = []

        # Read disable options and build the sub menu
        for disable_option in plugin_config['disable_options']:
            time_in_minutes = disable_option['time']
            label = []
            # Validate time value
            if not isinstance(time_in_minutes, int) or time_in_minutes <= 0:
                logging.error('Invalid time in disable option: ' + str(time_in_minutes))
                continue
            time_unit = disable_option['unit'].lower()
            if time_unit == 'seconds' or time_unit == 'second':
                time_in_minutes = int(time_in_minutes / 60)
                label = ['For %d Second', 'For %d Seconds']
            elif time_unit == 'minutes' or time_unit == 'minute':
                time_in_minutes = int(time_in_minutes * 1)
                label = ['For %d Minute', 'For %d Minutes']
            elif time_unit == 'hours' or time_unit == 'hour':
                time_in_minutes = int(time_in_minutes * 60)
                label = ['For %d Hour', 'For %d Hours']
            else:
                # Invalid unit
                logging.error('Invalid unit in disable option: ' + str(disable_option))
                continue

            # Create submenu
            sub_menu_item = Gtk.MenuItem()
            sub_menu_item.connect('activate', self.on_disable_clicked, time_in_minutes)
            self.sub_menu_items.append([sub_menu_item, label, disable_option['time']])
            self.sub_menu_disable.append(sub_menu_item)

        # Disable until restart submenu
        self.sub_menu_item_until_restart = Gtk.MenuItem()
        self.sub_menu_item_until_restart.connect('activate', self.on_disable_clicked, -1)
        self.sub_menu_disable.append(self.sub_menu_item_until_restart)

        # Add the sub menu to the enable/disable menu
        self.item_disable.set_submenu(self.sub_menu_disable)

        # Settings menu item
        self.item_manual_break = Gtk.MenuItem()
        self.item_manual_break.connect('activate', self.on_manual_break_clicked)

        # Settings menu item
        self.item_settings = Gtk.MenuItem()
        self.item_settings.connect('activate', self.show_settings)

        # About menu item
        self.item_about = Gtk.MenuItem()
        self.item_about.connect('activate', self.show_about)

        # Quit menu item
        self.item_quit = Gtk.MenuItem()
        self.item_quit.connect('activate', self.quit_safe_eyes)

        self.set_labels()

        # At startup, no need for activate menu
        self.item_enable.set_sensitive(False)

        # Append all menu items and show the menu
        self.menu.append(self.item_info)
        self.menu.append(self.item_separator)
        self.menu.append(self.item_enable)
        self.menu.append(self.item_disable)
        self.menu.append(self.item_manual_break)
        self.menu.append(self.item_settings)
        self.menu.append(self.item_about)
        self.menu.append(self.item_quit)
        self.menu.show_all()

        self.item_enable.set_visible(self.allow_disabling)
        self.item_disable.set_visible(self.allow_disabling)
        self.item_quit.set_visible(self.allow_disabling)
        self.item_quit.set_visible(self.allow_disabling)

        self.indicator.set_menu(self.menu)

    def initialize(self, plugin_config):
        """
        Initialize the tray icon by setting the config.
        """
        self.plugin_config = plugin_config
        self.set_labels()
        self.allow_disabling = plugin_config['allow_disabling']
        self.item_enable.set_visible(self.allow_disabling)
        self.item_disable.set_visible(self.allow_disabling)
        self.item_quit.set_visible(self.allow_disabling)
        self.item_quit.set_visible(self.allow_disabling)

    def set_labels(self):
        """
        Update the text of menu items based on the selected language.
        """
        for entry in self.sub_menu_items:
            # print(self.context['locale'].ngettext('For %d Hour', 'For %d Hours', 1) % 1)
            entry[0].set_label(self.context['locale'].ngettext(entry[1][0], entry[1][1], entry[2]) % entry[2])

        self.sub_menu_item_until_restart.set_label(_('Until restart'))
        self.item_enable.set_label(_('Enable Safe Eyes'))
        self.item_disable.set_label(_('Disable Safe Eyes'))

        breaks_found = self.has_breaks()
        if breaks_found:
            if self.active:
                if self.date_time:
                    self.__set_next_break_info()
                self.indicator.set_icon("safeeyes_enabled")
            else:
                if self.wakeup_time:
                    self.item_info.set_label(_('Disabled until %s') % utility.format_time(self.wakeup_time))
                else:
                    self.item_info.set_label(_('Disabled until restart'))
                self.indicator.set_label('', '')
                self.indicator.set_icon("safeeyes_disabled")
        else:
            self.item_info.set_label(_('No Breaks Available'))
            self.indicator.set_label('', '')
            self.indicator.set_icon("safeeyes_disabled")
        self.item_info.set_sensitive(breaks_found and self.active)
        self.item_enable.set_sensitive(breaks_found and not self.active)
        self.item_disable.set_sensitive(breaks_found and self.active)
        self.item_manual_break.set_sensitive(breaks_found and self.active)

        self.item_manual_break.set_label(_('Take a break now'))
        self.item_settings.set_label(_('Settings'))
        self.item_about.set_label(_('About'))
        self.item_quit.set_label(_('Quit'))

    def show_icon(self):
        """
        Show the tray icon.
        """
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

    def hide_icon(self):
        """
        Hide the tray icon.
        """
        self.indicator.set_status(appindicator.IndicatorStatus.PASSIVE)

    def quit_safe_eyes(self, *args):
        """
        Handle Quit menu action.
        This action terminates the application.
        """
        with self.lock:
            self.active = True
            # Notify all schedulers
            self.idle_condition.acquire()
            self.idle_condition.notify_all()
            self.idle_condition.release()
        self.quit()

    def show_settings(self, *args):
        """
        Handle Settings menu action.
        This action shows the Settings dialog.
        """
        self.on_show_settings()

    def show_about(self, *args):
        """
        Handle About menu action.
        This action shows the About dialog.
        """
        self.on_show_about()

    def next_break_time(self, dateTime):
        """
        Update the next break time to be displayed in the menu and optionally in the tray icon.
        """
        logging.info("Update next break information")
        self.date_time = dateTime
        self.__set_next_break_info()

    def __set_next_break_info(self):
        """
        A private method to be called within this class to update the next break information using self.dateTime.
        """
        formatted_time = utility.format_time(self.date_time)
        message = _('Next break at %s') % (formatted_time)
        # Update the menu item label
        utility.execute_main_thread(self.item_info.set_label, message)
        # Update the tray icon label
        if self.plugin_config.get('show_time_in_tray', False):
            self.indicator.set_label(formatted_time, '')
        else:
            self.indicator.set_label('', '')

    def on_manual_break_clicked(self, *args):
        """
        Trigger a break manually.
        """
        self.take_break()

    def on_enable_clicked(self, *args):
        """
        Handle 'Enable Safe Eyes' menu action.
        This action enables the application if it is currently disabled.
        """
        # active = self.item_enable.get_active()
        if not self.active:
            with self.lock:
                self.enable_ui()
                self.on_enable()
                # Notify all schedulers
                self.idle_condition.acquire()
                self.idle_condition.notify_all()
                self.idle_condition.release()

    def on_disable_clicked(self, *args):
        """
        Handle the menu actions of all the sub menus of 'Disable Safe Eyes'.
        This action disables the application if it is currently active.
        """
        # active = self.item_enable.get_active()
        if self.active and len(args) > 1:
            self.disable_ui()

            time_to_wait = args[1]
            if time_to_wait <= 0:
                info = _('Disabled until restart')
                self.on_disable(info)
                self.wakeup_time = None
                self.item_info.set_label(info)
            else:
                self.wakeup_time = datetime.datetime.now() + datetime.timedelta(minutes=time_to_wait)
                info = _('Disabled until %s') % utility.format_time(self.wakeup_time)
                self.on_disable(info)
                self.item_info.set_label(info)
                utility.start_thread(self.__schedule_resume, time_minutes=time_to_wait)

    def lock_menu(self):
        """
        This method is called by the core to prevent user from disabling Safe Eyes after the notification.
        """
        if self.active:
            self.menu.set_sensitive(False)

    def unlock_menu(self):
        """
        This method is called by the core to activate the menu after the the break.
        """
        if self.active:
            self.menu.set_sensitive(True)

    def disable_ui(self):
        """
        Change the UI to disabled state.
        """
        if self.active:
            logging.info('Disable Safe Eyes')
            self.active = False
            self.indicator.set_icon("safeeyes_disabled")
            self.item_info.set_label(_('Disabled until restart'))
            self.indicator.set_label('', '')
            self.item_info.set_sensitive(False)
            self.item_enable.set_sensitive(True)
            self.item_disable.set_sensitive(False)
            self.item_manual_break.set_sensitive(False)

    def enable_ui(self):
        """
        Change the UI to enabled state.
        """
        if not self.active:
            logging.info('Enable Safe Eyes')
            self.active = True
            self.indicator.set_icon("safeeyes_enabled")
            self.item_info.set_sensitive(True)
            self.item_enable.set_sensitive(False)
            self.item_disable.set_sensitive(True)
            self.item_manual_break.set_sensitive(True)

    def __schedule_resume(self, time_minutes):
        """
        Schedule a local timer to enable Safe Eyes after the given timeout.
        """
        self.idle_condition.acquire()
        self.idle_condition.wait(time_minutes * 60)    # Convert to seconds
        self.idle_condition.release()

        with self.lock:
            if not self.active:
                utility.execute_main_thread(self.item_enable.activate)

    def start_animation(self):
        if not self.active or not self.animate:
            return
        utility.execute_main_thread(lambda: self.indicator.set_icon("safeeyes_disabled"))
        time.sleep(0.5)
        utility.execute_main_thread(lambda: self.indicator.set_icon("safeeyes_enabled"))
        if self.animate and self.active:
            time.sleep(0.5)
            if self.animate and self.active:
                utility.start_thread(self.start_animation)

    def stop_animation(self):
        self.animate = False
        if self.active:
            utility.execute_main_thread(lambda: self.indicator.set_icon("safeeyes_enabled"))
        else:
            utility.execute_main_thread(lambda: self.indicator.set_icon("safeeyes_disabled"))

def init(ctx, safeeyes_cfg, plugin_config):
    """
    Initialize the tray icon.
    """
    global context
    global tray_icon
    global safeeyes_config
    logging.debug('Initialize Tray Icon plugin')
    context = ctx
    safeeyes_config = safeeyes_cfg
    if not tray_icon:
        tray_icon = TrayIcon(context, plugin_config)
    else:
        tray_icon.initialize(plugin_config)


def update_next_break(break_obj, next_break_time):
    """
    Update the next break time.
    """
    tray_icon.next_break_time(next_break_time)


def on_pre_break(break_obj):
    """
    Disable the menu if strict_break is enabled
    """
    if safeeyes_config.get('strict_break'):
        tray_icon.lock_menu()
    tray_icon.animate = True
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
