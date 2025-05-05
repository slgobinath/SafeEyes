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
"""SafeEyes connects all the individual components and provide the complete
application.
"""

import atexit
import logging
from threading import Timer
from importlib import metadata

import gi
from safeeyes import utility
from safeeyes.ui.about_dialog import AboutDialog
from safeeyes.ui.break_screen import BreakScreen
from safeeyes.ui.required_plugin_dialog import RequiredPluginDialog
from safeeyes.model import State, RequiredPluginException
from safeeyes.rpc import RPCServer
from safeeyes.plugin_manager import PluginManager
from safeeyes.core import SafeEyesCore
from safeeyes.ui.settings_dialog import SettingsDialog

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib

SAFE_EYES_VERSION = metadata.version("safeeyes")


class SafeEyes(Gtk.Application):
    """This class represents a runnable Safe Eyes instance."""

    required_plugin_dialog_active = False
    retry_errored_plugins_count = 0

    def __init__(self, system_locale, config, cli_args):
        super().__init__(
            application_id="io.github.slgobinath.SafeEyes",
            # This is necessary for compatibility with Ubuntu 22.04.
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.active = False
        self.break_screen = None
        self.safe_eyes_core = None
        self.config = config
        self.context = {}
        self.plugins_manager = None
        self.settings_dialog_active = False
        self.rpc_server = None
        self._status = ""
        self.cli_args = cli_args
        self.system_locale = system_locale

    def start(self):
        """Start Safe Eyes."""
        self.run()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        logging.info("Starting up Application")

        # Initialize the Safe Eyes Context
        self.context["version"] = SAFE_EYES_VERSION
        self.context["desktop"] = utility.desktop_environment()
        self.context["is_wayland"] = utility.is_wayland()
        self.context["locale"] = self.system_locale
        self.context["api"] = {}
        self.context["api"]["show_settings"] = lambda: utility.execute_main_thread(
            self.show_settings
        )
        self.context["api"]["show_about"] = lambda: utility.execute_main_thread(
            self.show_about
        )
        self.context["api"]["enable_safeeyes"] = (
            lambda next_break_time=-1, reset_breaks=False: utility.execute_main_thread(
                self.enable_safeeyes, next_break_time, reset_breaks
            )
        )
        self.context["api"]["disable_safeeyes"] = (
            lambda status=None, is_resting=False: utility.execute_main_thread(
                self.disable_safeeyes, status, is_resting
            )
        )
        self.context["api"]["status"] = self.status
        self.context["api"]["quit"] = lambda: utility.execute_main_thread(self.quit)
        if self.config.get("persist_state"):
            self.context["session"] = utility.open_session()
        else:
            self.context["session"] = {"plugin": {}}

        # Initialize the theme
        self._initialize_styles()

        self.break_screen = BreakScreen(
            self, self.context, self.on_skipped, self.on_postponed
        )
        self.break_screen.initialize(self.config)
        self.plugins_manager = PluginManager()
        self.safe_eyes_core = SafeEyesCore(self.context)
        self.safe_eyes_core.on_pre_break += self.plugins_manager.pre_break
        self.safe_eyes_core.on_start_break += self.on_start_break
        self.safe_eyes_core.start_break += self.start_break
        self.safe_eyes_core.on_count_down += self.countdown
        self.safe_eyes_core.on_stop_break += self.stop_break
        self.safe_eyes_core.on_update_next_break += self.update_next_break
        self.safe_eyes_core.initialize(self.config)
        self.context["api"]["take_break"] = self.take_break
        self.context["api"]["has_breaks"] = self.safe_eyes_core.has_breaks
        self.context["api"]["postpone"] = self.safe_eyes_core.postpone
        self.context["api"]["get_break_time"] = self.safe_eyes_core.get_break_time

        try:
            self.plugins_manager.init(self.context, self.config)
        except RequiredPluginException as e:
            self.show_required_plugin_dialog(e)

        self.hold()

        atexit.register(self.persist_session)

        if self.config.get("use_rpc_server", True):
            self.__start_rpc_server()

        if (
            not self.plugins_manager.needs_retry()
            and not self.required_plugin_dialog_active
            and self.safe_eyes_core.has_breaks()
        ):
            self.active = True
            self.context["state"] = State.START
            self.plugins_manager.start()  # Call the start method of all plugins
            self.safe_eyes_core.start()
            self.handle_system_suspend()

    def do_activate(self):
        logging.info("Application activated")

        if self.plugins_manager.needs_retry():
            GLib.timeout_add_seconds(1, self._retry_errored_plugins)

        if self.cli_args.about:
            self.show_about()
        elif self.cli_args.disable:
            self.disable_safeeyes()
        elif self.cli_args.enable:
            self.enable_safeeyes()
        elif self.cli_args.settings:
            self.show_settings()
        elif self.cli_args.take_break:
            self.take_break()

    def _initialize_styles(self):
        utility.load_css_file(
            utility.SYSTEM_STYLE_SHEET_PATH, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        utility.load_css_file(
            utility.CUSTOM_STYLE_SHEET_PATH,
            Gtk.STYLE_PROVIDER_PRIORITY_USER,
            required=False,
        )

    def _retry_errored_plugins(self):
        if not self.plugins_manager.needs_retry():
            return

        logging.info("Retry loading errored plugin")
        self.plugins_manager.retry_errored_plugins()

        error = self.plugins_manager.get_retryable_error()

        if error is None:
            # success
            self.restart(self.config, set_active=True)
            return

        # errored again
        if self.retry_errored_plugins_count >= 3:
            self.show_required_plugin_dialog(error)
            return

        timeout = pow(2, self.retry_errored_plugins_count)
        self.retry_errored_plugins_count += 1

        GLib.timeout_add_seconds(timeout, self._retry_errored_plugins)

    def show_settings(self):
        """Listen to tray icon Settings action and send the signal to Settings
        dialog.
        """
        if not self.settings_dialog_active:
            logging.info("Show Settings dialog")
            self.settings_dialog_active = True
            settings_dialog = SettingsDialog(
                self, self.config.clone(), self.save_settings
            )
            settings_dialog.show()

    def show_required_plugin_dialog(self, error: RequiredPluginException):
        self.required_plugin_dialog_active = True

        logging.info("Show RequiredPlugin dialog")
        plugin_id = error.get_plugin_id()

        dialog = RequiredPluginDialog(
            error.get_plugin_id(),
            error.get_plugin_name(),
            error.get_message(),
            self.quit,
            lambda: self.disable_plugin(plugin_id),
        )
        dialog.show()

    def disable_plugin(self, plugin_id):
        """Temporarily disable plugin, and restart SafeEyes."""
        config = self.config.clone()

        for plugin in config.get("plugins"):
            if plugin["id"] == plugin_id:
                plugin["enabled"] = False

        self.required_plugin_dialog_active = False

        self.restart(config, set_active=True)

    def show_about(self):
        """Listen to tray icon About action and send the signal to About
        dialog.
        """
        logging.info("Show About dialog")
        about_dialog = AboutDialog(self, SAFE_EYES_VERSION)
        about_dialog.show()

    def quit(self):
        """Listen to the tray menu quit action and stop the core, notification
        and the app itself.
        """
        logging.info("Quit Safe Eyes")
        self.break_screen.close()
        self.context["state"] = State.QUIT
        self.plugins_manager.stop()
        self.safe_eyes_core.stop()
        self.plugins_manager.exit()
        self.__stop_rpc_server()
        self.persist_session()

        super().quit()

    def handle_suspend_callback(self, sleeping):
        """If the system goes to sleep, Safe Eyes stop the core if it is
        already active.

        If it was active, Safe Eyes will become active after wake up.
        """
        if sleeping:
            # Sleeping / suspending
            if self.active:
                logging.info("Stop Safe Eyes due to system suspend")
                self.plugins_manager.stop()
                self.safe_eyes_core.stop(True)
        else:
            # Resume from sleep
            if self.active and self.safe_eyes_core.has_breaks():
                logging.info("Resume Safe Eyes after system wakeup")
                self.plugins_manager.start()
                self.safe_eyes_core.start()

    def handle_suspend_signal(self, proxy, sender, signal, parameters):
        if signal != "PrepareForSleep":
            return

        (sleeping,) = parameters

        self.handle_suspend_callback(sleeping)

    def handle_system_suspend(self):
        """Setup system suspend listener."""
        self.suspend_proxy = Gio.DBusProxy.new_for_bus_sync(
            bus_type=Gio.BusType.SYSTEM,
            flags=Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
            info=None,
            name="org.freedesktop.login1",
            object_path="/org/freedesktop/login1",
            interface_name="org.freedesktop.login1.Manager",
            cancellable=None,
        )
        self.suspend_proxy.connect("g-signal", self.handle_suspend_signal)

    def on_skipped(self):
        """Listen to break screen Skip action and send the signal to core."""
        logging.info("User skipped the break")
        self.safe_eyes_core.skip()
        self.plugins_manager.stop_break()

    def on_postponed(self):
        """Listen to break screen Postpone action and send the signal to
        core.
        """
        logging.info("User postponed the break")
        self.safe_eyes_core.postpone()
        self.plugins_manager.stop_break()

    def save_settings(self, config):
        """Listen to Settings dialog Save action and write to the config
        file.
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

        self.restart(config)

    def restart(self, config, set_active=False):
        logging.info("Initialize SafeEyesCore with modified settings")

        if self.rpc_server is None and config.get("use_rpc_server"):
            # RPC server wasn't running but now enabled
            self.__start_rpc_server()
        elif self.rpc_server is not None and not config.get("use_rpc_server"):
            # RPC server was running but now disabled
            self.__stop_rpc_server()

        # Restart the core and initialize the components
        self.config = config
        self.safe_eyes_core.initialize(config)
        self.break_screen.initialize(config)

        try:
            self.plugins_manager.init(self.context, self.config)
        except RequiredPluginException as e:
            self.show_required_plugin_dialog(e)
            return

        if set_active:
            self.active = True

        if self.active and self.safe_eyes_core.has_breaks():
            # 1 sec delay is required to give enough time for core to be stopped
            Timer(1.0, self.safe_eyes_core.start).start()
            self.plugins_manager.start()

    def enable_safeeyes(self, scheduled_next_break_time=-1, reset_breaks=False):
        """Listen to tray icon enable action and send the signal to core."""
        if (
            not self.required_plugin_dialog_active
            and not self.active
            and self.safe_eyes_core.has_breaks()
        ):
            self.active = True
            self.safe_eyes_core.start(scheduled_next_break_time, reset_breaks)
            self.plugins_manager.start()

    def disable_safeeyes(self, status=None, is_resting=False):
        """Listen to tray icon disable action and send the signal to core."""
        if self.active:
            self.active = False
            self.plugins_manager.stop()
            self.safe_eyes_core.stop(is_resting)
            if status is None:
                status = _("Disabled until restart")
            self._status = status

    def on_start_break(self, break_obj):
        """Pass the break information to plugins."""
        if not self.plugins_manager.start_break(break_obj):
            return False
        return True

    def start_break(self, break_obj):
        """Pass the break information to break screen."""
        # Get the HTML widgets content from plugins
        widget = self.plugins_manager.get_break_screen_widgets(break_obj)
        actions = self.plugins_manager.get_break_screen_tray_actions(break_obj)
        self.break_screen.show_message(break_obj, widget, actions)

    def countdown(self, countdown, seconds):
        """Pass the countdown to plugins and break screen."""
        self.break_screen.show_count_down(countdown, seconds)
        self.plugins_manager.countdown(countdown, seconds)
        return True

    def update_next_break(self, break_obj, break_time):
        """Update the next break to plugins and save the session."""
        self.plugins_manager.update_next_break(break_obj, break_time)
        self._status = _("Next break at %s") % (utility.format_time(break_time))
        if self.config.get("persist_state"):
            utility.write_json(utility.SESSION_FILE_PATH, self.context["session"])

    def stop_break(self):
        """Stop the current break."""
        self.break_screen.close()
        self.plugins_manager.stop_break()
        return True

    def take_break(self, break_type=None):
        """Take a break now."""
        utility.execute_main_thread(self.safe_eyes_core.take_break, break_type)

    def status(self):
        """Return the status of Safe Eyes."""
        return self._status

    def persist_session(self):
        """Save the session object to the session file."""
        if self.config.get("persist_state"):
            utility.write_json(utility.SESSION_FILE_PATH, self.context["session"])
        else:
            utility.delete(utility.SESSION_FILE_PATH)

    def __start_rpc_server(self):
        if self.rpc_server is None:
            self.rpc_server = RPCServer(self.config.get("rpc_port"), self.context)
            self.rpc_server.start()

    def __stop_rpc_server(self):
        if self.rpc_server is not None:
            self.rpc_server.stop()
            self.rpc_server = None
