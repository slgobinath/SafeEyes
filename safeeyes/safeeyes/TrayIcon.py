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

import gi, logging, threading, datetime, Utility
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk
from gi.repository import AppIndicator3 as appindicator

# Global variables
APPINDICATOR_ID = 'safeeyes'


class TrayIcon:

    def __init__(self, config, language, on_show_settings, on_show_about, on_enable, on_disable, on_quite):
        logging.info("Initialize the tray icon")
        self.on_show_settings = on_show_settings
        self.on_show_about = on_show_about
        self.on_quite = on_quite
        self.on_enable = on_enable
        self.on_disable = on_disable
        self.language = language
        self.dateTime = None
        self.active = True
        self.idle_condition = threading.Condition()
        self.lock = threading.Lock()

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

        # Enable/Disable menu item
        self.item_enable = Gtk.MenuItem()
        self.item_enable.connect('activate', self.on_toogle_enable)

        self.sub_menu_disable = Gtk.Menu()
        self.sub_menu_items = []

        # Read disable options and build the sub menu
        for disable_option in config['disable_options']:
            time_in_minutes = disable_option['time']
            # Validate time value
            if not isinstance(time_in_minutes, int) or time_in_minutes <= 0:
                logging.error('Invalid time in disable option: ' + str(time_in_minutes))
                continue
            time_unit = disable_option['unit'].lower()
            if time_unit == 'seconds' or time_unit == 'second':
                time_in_minutes = int(time_in_minutes / 60)
            elif time_unit == 'minutes' or time_unit == 'minute':
                time_in_minutes = int(time_in_minutes * 1)
            elif time_unit == 'hours' or time_unit == 'hour':
                time_in_minutes = int(time_in_minutes * 60)
            else:
                # Invalid unit
                logging.error('Invalid unit in disable option: ' + str(disable_option))
                continue

            # Create submenu
            sub_menu_item = Gtk.MenuItem()
            sub_menu_item.connect('activate', self.on_toogle_enable, time_in_minutes)
            self.sub_menu_items.append([sub_menu_item, disable_option['label'], disable_option['time']])
            self.sub_menu_disable.append(sub_menu_item)

        # Disable until restart submenu
        self.sub_menu_item_until_restart = Gtk.MenuItem()
        self.sub_menu_item_until_restart.connect('activate', self.on_toogle_enable, -1)
        self.sub_menu_disable.append(self.sub_menu_item_until_restart)

        # Add the sub menu to the enable/disable menu
        self.item_enable.set_submenu(self.sub_menu_disable)

        # Settings menu item
        self.item_settings = Gtk.MenuItem()
        self.item_settings.connect('activate', self.show_settings)

        # About menu item
        self.item_about = Gtk.MenuItem()
        self.item_about.connect('activate', self.show_about)

        # Quit menu item
        self.item_quit = Gtk.MenuItem()
        self.item_quit.connect('activate', self.quit_safe_eyes)

        self.set_labels(language)

        # Append all menu items and show the menu
        self.menu.append(self.item_info)
        self.menu.append(self.item_separator)
        self.menu.append(self.item_enable)
        self.menu.append(self.item_settings)
        self.menu.append(self.item_about)
        self.menu.append(self.item_quit)
        self.menu.show_all()

        self.indicator.set_menu(self.menu)

    def set_labels(self, language):
        self.language = language
        for entry in self.sub_menu_items:
            entry[0].set_label(self.language['ui_controls'][entry[1]].format(entry[2]))
        self.sub_menu_item_until_restart.set_label(self.language['ui_controls']['until_restart'])
        self.item_info.set_label(self.language['messages']['disabled_until_restart'])
        self.item_enable.set_label(self.language['ui_controls']['disable'])
        self.item_settings.set_label(self.language['ui_controls']['settings'])
        self.item_about.set_label(self.language['ui_controls']['about'])
        self.item_quit.set_label(self.language['ui_controls']['quit'])

    def show_icon(self):
        Utility.execute_main_thread(self.indicator.set_status, appindicator.IndicatorStatus.ACTIVE)

    def hide_icon(self):
        Utility.execute_main_thread(self.indicator.set_status, appindicator.IndicatorStatus.PASSIVE)

    def quit_safe_eyes(self, *args):
        self.on_quite()
        with self.lock:
            self.active = True
            # Notify all schedulers
            self.idle_condition.acquire()
            self.idle_condition.notify_all()
            self.idle_condition.release()

    def show_settings(self, *args):
        self.on_show_settings()

    def show_about(self, *args):
        self.on_show_about()

    def next_break_time(self, dateTime):
        logging.info("Update next break information")
        self.dateTime = dateTime
        self.set_next_break_info(self.dateTime)

    def set_next_break_info(self, dateTime):
        formatted_time = Utility.format_time(dateTime)
        message = self.language['messages'][
            'next_break_at'].format(formatted_time)

        Utility.execute_main_thread(self.item_info.set_label, message)

    def on_toogle_enable(self, *args):
        # active = self.item_enable.get_active()
        if args[0] == self.item_enable and not self.active:
            with self.lock:
                logging.info('Enable Safe Eyes')
                self.active = True
                self.indicator.set_icon("safeeyes_enabled")
                self.item_info.set_sensitive(True)
                self.on_enable()
                self.item_enable.set_label(self.language['ui_controls']['disable'])
                self.item_enable.set_submenu(self.sub_menu_disable)
                # Notify all schedulers
                self.idle_condition.acquire()
                self.idle_condition.notify_all()
                self.idle_condition.release()
        elif args[0] != self.item_enable and self.active:
            logging.info('Disable Safe Eyes')
            self.active = False
            self.indicator.set_icon("safeeyes_disabled")
            self.item_info.set_sensitive(False)
            self.on_disable()
            self.item_enable.set_label(self.language['ui_controls']['enable'])
            self.item_enable.set_submenu(None)

            time_to_wait = args[1]
            if time_to_wait <= 0:
                self.item_info.set_label(self.language['messages']['disabled_until_restart'])
            else:
                wakeup_time = datetime.datetime.now() + datetime.timedelta(minutes=time_to_wait)
                Utility.start_thread(self.__schedule_resume, time_minutes=time_to_wait)
                self.item_info.set_label(self.language['messages']['disabled_until_x'].format(Utility.format_time(wakeup_time)))


    def __schedule_resume(self, time_minutes):
        self.idle_condition.acquire()
        self.idle_condition.wait(time_minutes * 60) # Convert to seconds
        self.idle_condition.release()

        with self.lock:
            if not self.active:
                Utility.execute_main_thread(self.item_enable.activate)
