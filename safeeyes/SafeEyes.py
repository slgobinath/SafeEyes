#!/usr/bin/env python
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
"""
SafeEyes connects all the individual components and provide the complete application.
"""

import atexit
import logging
from threading import Timer

import dbus
import gi
from dbus.mainloop.glib import DBusGMainLoop
from safeeyes import Utility
from safeeyes.AboutDialog import AboutDialog
from safeeyes.BreakScreen import BreakScreen
from safeeyes.model import State
from safeeyes.model import Config
from safeeyes.PluginManager import PluginManager
from safeeyes.SafeEyesCore import SafeEyesCore
from safeeyes.settings import SettingsDialog

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

SAFE_EYES_VERSION = "2.0.0"


class SafeEyes(object):
    """
    This class represents a runnable Safe Eyes instance.
    """

    def __init__(self, system_locale):
        self.active = True
        self.break_screen = None
        self.safe_eyes_core = None
        self.config = None
        self.context = {}
        self.plugins_manager = None
        self.settings_dialog_active = False

        self.config = Config()

        # Initialize the Safe Eyes Context
        self.context['version'] = SAFE_EYES_VERSION
        self.context['desktop'] = Utility.desktop_environment()
        self.context['locale'] = system_locale
        self.context['api'] = {}
        self.context['api']['show_settings'] = self.show_settings
        self.context['api']['show_about'] = self.show_about
        self.context['api']['enable_safeeyes'] = self.enable_safeeyes
        self.context['api']['disable_safeeyes'] = self.disable_safeeyes
        self.context['api']['on_quit'] = self.on_quit
        if self.config.get('persist_state'):
            self.context['session'] = Utility.open_session()
        else:
            self.context['session'] = {'plugin': {}}

        self.break_screen = BreakScreen(self.context, self.on_skipped, self.on_postponed, Utility.STYLE_SHEET_PATH)
        self.break_screen.initialize(self.config)
        self.plugins_manager = PluginManager(self.context, self.config)
        self.safe_eyes_core = SafeEyesCore(self.context)
        self.safe_eyes_core.on_pre_break += self.plugins_manager.pre_break
        self.safe_eyes_core.on_start_break += self.start_break
        self.safe_eyes_core.on_count_down += self.countdown
        self.safe_eyes_core.on_stop_break += self.stop_break
        self.safe_eyes_core.on_update_next_break += self.update_next_break
        self.safe_eyes_core.initialize(self.config)
        self.context['api']['take_break'] = self.safe_eyes_core.take_break
        self.plugins_manager.init(self.context, self.config)
        atexit.register(self.persist_session)

    def start(self):
        """
        Start Safe Eyes
        """
        self.context['state'] = State.START
        self.plugins_manager.start()		# Call the start method of all plugins
        self.safe_eyes_core.start()
        self.handle_system_suspend()

    def show_settings(self):
        """
        Listen to tray icon Settings action and send the signal to Settings dialog.
        """
        if not self.settings_dialog_active:
            logging.info("Show Settings dialog")
            self.settings_dialog_active = True
            settings_dialog = SettingsDialog(self.config, self.save_settings)
            settings_dialog.show()

    def show_about(self):
        """
        Listen to tray icon About action and send the signal to About dialog.
        """
        logging.info("Show About dialog")
        about_dialog = AboutDialog(SAFE_EYES_VERSION)
        about_dialog.show()

    def on_quit(self):
        """
        Listen to the tray menu quit action and stop the core, notification and the app itself.
        """
        logging.info("Quit Safe Eyes")
        self.context['state'] = State.QUIT
        self.plugins_manager.stop()
        self.safe_eyes_core.stop()
        self.plugins_manager.exit()
        Gtk.main_quit()

    def handle_suspend_callback(self, sleeping):
        """
        If the system goes to sleep, Safe Eyes stop the core if it is already active.
        If it was active, Safe Eyes will become active after wake up.
        """
        if sleeping:
            # Sleeping / suspending
            if self.active:
                logging.info("Stop Safe Eyes due to system suspend")
                self.plugins_manager.stop()
                self.safe_eyes_core.stop()
        else:
            # Resume from sleep
            if self.active:
                logging.info("Resume Safe Eyes after system wakeup")
                self.plugins_manager.start()
                self.safe_eyes_core.start()

    def handle_system_suspend(self):
        """
        Setup system suspend listener.
        """
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        bus.add_signal_receiver(self.handle_suspend_callback, 'PrepareForSleep', 'org.freedesktop.login1.Manager', 'org.freedesktop.login1')

    def on_skipped(self):
        """
        Listen to break screen Skip action and send the signal to core.
        """
        logging.info("User skipped the break")
        self.safe_eyes_core.skip()
        self.plugins_manager.stop_break()

    def on_postponed(self):
        """
        Listen to break screen Postpone action and send the signal to core.
        """
        logging.info("User postponed the break")
        self.safe_eyes_core.postpone()
        self.plugins_manager.stop_break()

    def save_settings(self, config):
        """
        Listen to Settings dialog Save action and write to the config file.
        """
        self.settings_dialog_active = False
        logging.info("Saving settings to safeeyes.json")

        # Stop the Safe Eyes core
        if self.active:
            self.plugins_manager.stop()
            self.safe_eyes_core.stop()

        # Write the configuration to file
        config.save()
        self.persist_session()

        logging.info("Initialize SafeEyesCore with modified settings")

        # Restart the core and intialize the components
        self.config = config
        self.safe_eyes_core.initialize(config)
        self.break_screen.initialize(config)
        self.plugins_manager.init(self.context, self.config)
        if self.active:
            # 1 sec delay is required to give enough time for core to be stopped
            Timer(1.0, self.safe_eyes_core.start).start()
            self.plugins_manager.start()

    def enable_safeeyes(self):
        """
        Listen to tray icon enable action and send the signal to core.
        """
        self.active = True
        self.safe_eyes_core.start()
        self.plugins_manager.start()

    def disable_safeeyes(self):
        """
        Listen to tray icon disable action and send the signal to core.
        """
        self.active = False
        self.plugins_manager.stop()
        self.safe_eyes_core.stop()

    def start_break(self, break_obj):
        """
        Pass the break information to plugins and break screen.
        """
        if not self.plugins_manager.start_break(break_obj):
            return False
        # Get the HTML widgets content from plugins
        widget = self.plugins_manager.get_break_screen_widgets(break_obj)
        self.break_screen.show_message(break_obj, widget)
        return True

    def countdown(self, countdown, seconds):
        """
        Pass the countdown to plugins and break screen.
        """
        self.break_screen.show_count_down(countdown, seconds)
        self.plugins_manager.countdown(countdown, seconds)
        return True

    def update_next_break(self, break_time):
        """
        Update the next break to plugins and save the session.
        """
        self.plugins_manager.update_next_break(break_time)
        if self.config.get('persist_state'):
            Utility.write_json(Utility.SESSION_FILE_PATH, self.context['session'])

    def stop_break(self):
        """
        Stop the current break.
        """
        self.break_screen.close()
        self.plugins_manager.stop_break()
        return True

    def persist_session(self):
        """
        Save the session object to the session file.
        """
        if self.config.get('persist_state'):
            Utility.write_json(Utility.SESSION_FILE_PATH, self.context['session'])
        else:
            Utility.delete(Utility.SESSION_FILE_PATH)
