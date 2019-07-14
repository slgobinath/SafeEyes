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
import os
from threading import Timer

import dbus
import gi
from dbus.mainloop.glib import DBusGMainLoop
from safeeyes import Utility
from safeeyes.AboutDialog import AboutDialog
from safeeyes.BreakScreen import BreakScreen
from safeeyes.model import State
from safeeyes.rpc import RPCServer
from safeeyes.PluginManager import PluginManager
from safeeyes.SafeEyesCore import SafeEyesCore
from safeeyes.settings import SettingsDialog

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

SAFE_EYES_VERSION = "2.0.9"


class SafeEyes(object):
    """
    This class represents a runnable Safe Eyes instance.
    """

    def __init__(self, system_locale, config):
        self.active = False
        self.break_screen = None
        self.safe_eyes_core = None
        self.config = config
        self.context = {}
        self.plugins_manager = None
        self.settings_dialog_active = False
        self.rpc_server = None
        self._status = ''

        # Initialize the Safe Eyes Context
        self.context['version'] = SAFE_EYES_VERSION
        self.context['desktop'] = Utility.desktop_environment()
        self.context['is_wayland'] = Utility.is_wayland()
        self.context['locale'] = system_locale
        self.context['api'] = {}
        self.context['api']['show_settings'] = lambda: Utility.execute_main_thread(
            self.show_settings)
        self.context['api']['show_about'] = lambda: Utility.execute_main_thread(
            self.show_about)
        self.context['api']['enable_safeeyes'] = lambda next_break_time=- \
            1: Utility.execute_main_thread(self.enable_safeeyes, next_break_time)
        self.context['api']['disable_safeeyes'] = lambda status: Utility.execute_main_thread(
            self.disable_safeeyes, status)
        self.context['api']['status'] = self.status
        self.context['api']['quit'] = lambda: Utility.execute_main_thread(
            self.quit)
        if self.config.get('persist_state'):
            self.context['session'] = Utility.open_session()
        else:
            self.context['session'] = {'plugin': {}}

        self.break_screen = BreakScreen(
            self.context, self.on_skipped, self.on_postponed, Utility.STYLE_SHEET_PATH)
        self.break_screen.initialize(self.config)
        self.plugins_manager = PluginManager(self.context, self.config)
        self.safe_eyes_core = SafeEyesCore(self.context)
        self.safe_eyes_core.on_pre_break += self.plugins_manager.pre_break
        self.safe_eyes_core.on_start_break += self.on_start_break
        self.safe_eyes_core.start_break += self.start_break
        self.safe_eyes_core.on_count_down += self.countdown
        self.safe_eyes_core.on_stop_break += self.stop_break
        self.safe_eyes_core.on_update_next_break += self.update_next_break
        self.safe_eyes_core.initialize(self.config)
        self.context['api']['take_break'] = lambda: Utility.execute_main_thread(
            self.safe_eyes_core.take_break)
        self.context['api']['has_breaks'] = self.safe_eyes_core.has_breaks
        self.context['api']['postpone'] = self.safe_eyes_core.postpone
        self.plugins_manager.init(self.context, self.config)
        atexit.register(self.persist_session)
        self.rpc_server = RPCServer(self.config.get('rpc_port'), self.context)
        self.rpc_server.start()

    def start(self):
        """
        Start Safe Eyes
        """
        if self.safe_eyes_core.has_breaks():
            self.active = True
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
            settings_dialog = SettingsDialog(
                self.config.clone(), self.save_settings)
            settings_dialog.show()

    def show_about(self):
        """
        Listen to tray icon About action and send the signal to About dialog.
        """
        logging.info("Show About dialog")
        about_dialog = AboutDialog(SAFE_EYES_VERSION)
        about_dialog.show()

    def quit(self):
        """
        Listen to the tray menu quit action and stop the core, notification and the app itself.
        """
        logging.info("Quit Safe Eyes")
        self.context['state'] = State.QUIT
        self.plugins_manager.stop()
        self.safe_eyes_core.stop()
        self.plugins_manager.exit()
        self.rpc_server.stop()
        self.persist_session()
        Gtk.main_quit()
        # Exit all threads
        os._exit(0)

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
            if self.active and self.safe_eyes_core.has_breaks():
                logging.info("Resume Safe Eyes after system wakeup")
                self.plugins_manager.start()
                self.safe_eyes_core.start()

    def handle_system_suspend(self):
        """
        Setup system suspend listener.
        """
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        bus.add_signal_receiver(self.handle_suspend_callback, 'PrepareForSleep',
                                'org.freedesktop.login1.Manager', 'org.freedesktop.login1')

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

        if self.config == config:
            # Config is not modified
            return

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
        if self.active and self.safe_eyes_core.has_breaks():
            # 1 sec delay is required to give enough time for core to be stopped
            Timer(1.0, self.safe_eyes_core.start).start()
            self.plugins_manager.start()

    def enable_safeeyes(self, scheduled_next_break_time=-1):
        """
        Listen to tray icon enable action and send the signal to core.
        """
        if not self.active and self.safe_eyes_core.has_breaks():
            self.active = True
            self.safe_eyes_core.start(scheduled_next_break_time)
            self.plugins_manager.start()

    def disable_safeeyes(self, status=None):
        """
        Listen to tray icon disable action and send the signal to core.
        """
        if self.active:
            self.active = False
            self.plugins_manager.stop()
            self.safe_eyes_core.stop()
            if status is None:
                status = _('Disabled until restart')
            self._status = status

    def on_start_break(self, break_obj):
        """
        Pass the break information to plugins.
        """
        if not self.plugins_manager.start_break(break_obj):
            return False
        return True

    def start_break(self, break_obj):
        """
        Pass the break information to break screen.
        """
        # Get the HTML widgets content from plugins
        widget = self.plugins_manager.get_break_screen_widgets(break_obj)
        actions = self.plugins_manager.get_break_screen_tray_actions(break_obj)
        self.break_screen.show_message(break_obj, widget, actions)

    def countdown(self, countdown, seconds):
        """
        Pass the countdown to plugins and break screen.
        """
        self.break_screen.show_count_down(countdown, seconds)
        self.plugins_manager.countdown(countdown, seconds)
        return True

    def update_next_break(self, break_obj, break_time):
        """
        Update the next break to plugins and save the session.
        """
        self.plugins_manager.update_next_break(break_obj, break_time)
        self._status = _('Next break at %s') % (
            Utility.format_time(break_time))
        if self.config.get('persist_state'):
            Utility.write_json(Utility.SESSION_FILE_PATH,
                               self.context['session'])

    def stop_break(self):
        """
        Stop the current break.
        """
        self.break_screen.close()
        self.plugins_manager.stop_break()
        return True

    def take_break(self):
        """
        Take a break now.
        """
        self.safe_eyes_core.take_break()

    def status(self):
        """
        Return the status of Safe Eyes.
        """
        return self._status

    def persist_session(self):
        """
        Save the session object to the session file.
        """
        if self.config.get('persist_state'):
            Utility.write_json(Utility.SESSION_FILE_PATH,
                               self.context['session'])
        else:
            Utility.delete(Utility.SESSION_FILE_PATH)
