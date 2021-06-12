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
import datetime
import logging
import sys

import dbus
import gi
from dbus.mainloop.glib import DBusGMainLoop

from safeeyes.breaks.scheduler import BreakScheduler
from safeeyes.config import Config
from safeeyes.context import Context
from safeeyes.plugin_utils.loader import PluginLoader
from safeeyes.plugin_utils.manager import PluginManager
from safeeyes.spi.api import CoreAPI
from safeeyes.spi.state import State
from safeeyes.thread import Heartbeat, main
from safeeyes.ui.UIManager import UIManager
from safeeyes.util import locale

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class SafeEyes(CoreAPI):
    """
    This class represents a runnable Safe Eyes instance.
    """

    def __init__(self, system_locale, config: Config):
        self.__context: Context = Context(config, locale.init_locale())
        self.__plugin_loader = PluginLoader()
        self.__heartbeat = Heartbeat(self.__context)
        self.__plugin_manager: PluginManager = PluginManager(self.__plugin_loader.load(self.__context))
        self.__scheduler: BreakScheduler = BreakScheduler(self.__context, self.__heartbeat, self.__plugin_manager)
        self.__ui_manager: UIManager = UIManager(self.__context, self.__on_config_changed)
        self.__active = False
        self.__context.set_apis(self, self.__heartbeat, self.__ui_manager, self.__scheduler, self.__plugin_manager)

        self.__plugin_manager.init(self.__context)
        # Save the session on exit
        atexit.register(self.__persist_session)

    def start(self, scheduled_next_break_time: datetime.datetime = None, reset_breaks=False):
        """
        Listen to tray icon enable action and send the signal to core.
        """
        """
        Start Safe Eyes
        """
        self.__heartbeat.start()
        if not self.__active and self.__scheduler.has_breaks():
            self.__active = True
            self.__context.state = State.START
            self.__plugin_manager.on_start()  # Call the start method of all plugins
            # todo: reset breaks
            self.__scheduler.start(scheduled_next_break_time)
            self.__handle_system_suspend()

    def stop(self):
        """
        Listen to tray icon disable action and send the signal to core.
        """
        """
        Stop Safe Eyes
        """
        logging.info("Stop safe eyes")
        self.__context.state = State.STOPPED
        if self.__active:
            self.__active = False
            self.__plugin_manager.on_stop()
            self.__scheduler.stop()
            self.__heartbeat.stop()
            self.__handle_system_suspend()
        self.__persist_session()

    @main
    def quit(self):
        self.stop()
        logging.info("Quit safe eyes")
        self.__context.state = State.QUIT
        Gtk.main_quit()
        # Exit all threads
        # os._exit(0)
        sys.exit(0)

    def __persist_session(self):
        """
        Save the session object to the session file.
        """
        self.__context.session.save(self.__context.config.get('persist_state', False))

    def __start_rpc_server(self):
        # if self.rpc_server is None:
        #     self.rpc_server = RPCServer(self.__context.config.get('rpc_port'), self.context)
        #     self.rpc_server.start()
        pass

    def __stop_rpc_server(self):
        # if self.rpc_server is not None:
        #     self.rpc_server.stop()
        #     self.rpc_server = None
        pass

    def __on_config_changed(self, config: Config):
        is_active = self.__active
        if is_active:
            self.stop()

        logging.info("Save the safeeyes.json")
        config.save()

        logging.info("Initialize safe eyes with the modified config")

        # Restart the core and initialize the components
        self.__context.config = config
        self.__plugin_manager = PluginManager(self.__plugin_loader.load(self.__context))
        self.__scheduler = BreakScheduler(self.__context, self.__heartbeat, self.__plugin_manager)
        self.__plugin_manager.init(self.__context)
        self.__context.set_apis(self, self.__heartbeat, self.__ui_manager, self.__scheduler, self.__plugin_manager)

        if is_active:
            self.start()

    def __handle_suspend_callback(self, sleeping):
        """
        If the system goes to sleep, Safe Eyes stop the core if it is already active.
        If it was active, Safe Eyes will become active after wake up.
        """
        if sleeping:
            # Sleeping / suspending
            if self.__active:
                logging.info("Stop Safe Eyes due to system suspend")
                self.__plugin_manager.on_stop()
                self.__scheduler.stop()
        else:
            # Resume from sleep
            if self.__active and self.__scheduler.has_breaks():
                logging.info("Resume Safe Eyes after system wakeup")
                self.__plugin_manager.on_start()
                self.__scheduler.start()

    def __handle_system_suspend(self):
        """
        Setup system suspend listener.
        """
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        if self.__active:
            bus.add_signal_receiver(self.__handle_suspend_callback, 'PrepareForSleep',
                                    'org.freedesktop.login1.Manager', 'org.freedesktop.login1')
        else:
            bus.remove_signal_receiver(self.__handle_suspend_callback, 'PrepareForSleep',
                                       'org.freedesktop.login1.Manager', 'org.freedesktop.login1')
