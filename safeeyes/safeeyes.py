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
from importlib import metadata
import typing

import gi
from safeeyes import context, utility
from safeeyes.ui.about_dialog import AboutDialog
from safeeyes.ui.break_screen import BreakScreen
from safeeyes.ui.required_plugin_dialog import RequiredPluginDialog
from safeeyes.model import BreakType, State, RequiredPluginException
from safeeyes.translations import translate as _
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
    context: context.Context
    break_screen: BreakScreen
    safe_eyes_core: SafeEyesCore
    plugins_manager: PluginManager
    system_locale: str

    _settings_dialog: typing.Optional[SettingsDialog] = None

    def __init__(self, system_locale: str, config) -> None:
        super().__init__(
            application_id="io.github.slgobinath.SafeEyes",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )

        self.active = False
        self.config = config
        self._status = ""
        self.system_locale = system_locale

        self.__register_cli_arguments()
        self.__register_actions()

    def __register_cli_arguments(self):
        flags = [
            # startup window
            ("about", "a", _("show the about dialog")),
            ("settings", "s", _("show the settings dialog")),
            ("take-break", "t", _("Take a break now").lower()),
            # activate action
            ("disable", "d", _("disable the currently running Safe Eyes instance")),
            ("enable", "e", _("enable the currently running Safe Eyes instance")),
            ("quit", "q", _("quit the running Safe Eyes instance and exit")),
            # special handling
            (
                "status",
                None,
                _("print the status of running Safe Eyes instance and exit"),
            ),
            # toggle
            ("debug", None, _("start Safe Eyes in debug mode")),
            # TODO: translate
            ("version", None, "show program's version number and exit"),
        ]

        for flag, short, desc in flags:
            # all flags are booleans
            self.add_main_option(
                flag,
                ord(short) if short else 0,
                GLib.OptionFlags.NONE,
                GLib.OptionArg.NONE,
                desc,
                None,
            )

    def __register_actions(self) -> None:
        actions = [
            ("show_about", self.show_about),
            ("show_settings", self.show_settings),
            ("take_break", self.take_break),
            ("enable_safeeyes", self.enable_safeeyes),
            ("disable_safeeyes", self.disable_safeeyes),
            ("quit", self.quit),
        ]

        # this is needed because of late bindings...
        def create_cb_discard_args(callback):
            return lambda parameter, user_data: callback()

        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", create_cb_discard_args(callback))
            self.add_action(action)

    def do_handle_local_options(self, options):
        Gtk.Application.do_handle_local_options(self, options)

        # do not call options.end() here - this will clear the dict,
        # and make it empty/broken inside do_command_line

        debug = False
        if options.contains("debug"):
            debug = True

        # Initialize the logging
        utility.initialize_logging(debug)
        utility.initialize_platform()
        utility.cleanup_old_user_stylesheet()

        if options.contains("version"):
            print(f"Safe Eyes {SAFE_EYES_VERSION}")
            return 0  # exit

        # needed for calling is_remote
        self.register(None)

        is_remote = self.get_is_remote()

        if is_remote:
            logging.info("Remote instance")

            if options.contains("status"):
                # fall through the default handling
                # this will call do_command_line on the primary instance
                # where we will handle this
                return -1

            if options.contains("quit"):
                self.activate_action("quit", None)
                return 0

            if options.contains("enable"):
                self.activate_action("enable_safeeyes", None)
                return 0

            if options.contains("disable"):
                self.activate_action("disable_safeeyes", None)
                return 0

            if options.contains("about"):
                self.activate_action("show_about", None)
                return 0

            if options.contains("settings"):
                self.activate_action("show_settings", None)
                return 0

            if options.contains("take-break"):
                self.activate_action("take_break", None)
                return 0

            logging.info("Safe Eyes is already running")
            return 0  # TODO: return error code here?

        else:
            logging.info("Primary instance")

            if (
                options.contains("enable")
                or options.contains("disable")
                or options.contains("status")
                or options.contains("quit")
            ):
                print(_("Safe Eyes is not running"))
                self.activate_action("quit", None)
                return 1

        return -1  # continue default handling

    def do_command_line(self, command_line):
        Gtk.Application.do_command_line(self, command_line)

        cli = command_line.get_options_dict().end().unpack()

        if cli.get("status"):
            # this is only invoked remotely
            # this code runs in the primary instance, but will print to the output
            # of the remote instance
            command_line.print_literal(self.status())
            return 0

        logging.info("Handle primary command line")

        self.activate()

        if cli.get("about"):
            self.show_about()
        elif cli.get("settings"):
            self.show_settings()
        elif cli.get("take-break"):
            self.take_break()

        return 0

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)

        logging.info("Starting up Application")

        # Initialize the Safe Eyes Context
        if self.config.get("persist_state"):
            session = utility.open_session()
        else:
            session = {"plugin": {}}

        self.context = context.Context(
            api=context.API(self),
            locale=self.system_locale,
            version=SAFE_EYES_VERSION,
            session=session,
        )

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

        try:
            self.plugins_manager.init(self.context, self.config)
        except RequiredPluginException as e:
            self.show_required_plugin_dialog(e)

        self.hold()

        atexit.register(self.persist_session)

        if (
            not self.plugins_manager.needs_retry()
            and not self.required_plugin_dialog_active
            and self.safe_eyes_core.has_breaks()
        ):
            self.active = True
            self.context.state = State.START
            self.plugins_manager.start()  # Call the start method of all plugins
            self.safe_eyes_core.start()
            self.handle_system_suspend()

    def do_activate(self):
        logging.info("Application activated")

        if self.plugins_manager.needs_retry():
            GLib.timeout_add_seconds(1, self._retry_errored_plugins)

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

    def show_settings(self, activation_token: typing.Optional[str] = None) -> None:
        """Listen to tray icon Settings action and send the signal to Settings
        dialog.
        """
        if self._settings_dialog is None:
            logging.info("Show Settings dialog")
            self._settings_dialog = SettingsDialog(
                self, self.config.clone(), self.save_settings
            )

        if activation_token is not None:
            self._settings_dialog.set_startup_id(activation_token)

        self._settings_dialog.show()

    def show_required_plugin_dialog(self, error: RequiredPluginException) -> None:
        self.required_plugin_dialog_active = True

        logging.info("Show RequiredPlugin dialog")
        plugin_id = error.get_plugin_id()

        dialog = RequiredPluginDialog(
            error.get_plugin_name(),
            error.get_message(),
            self.quit,
            lambda: self.disable_plugin(plugin_id),
            application=self,
        )
        dialog.show()

    def disable_plugin(self, plugin_id):
        """Temporarily disable plugin, and restart Safe Eyes."""
        config = self.config.clone()

        for plugin in config.get("plugins"):
            if plugin["id"] == plugin_id:
                plugin["enabled"] = False

        self.required_plugin_dialog_active = False

        self.restart(config, set_active=True)

    def show_about(self, activation_token: typing.Optional[str] = None):
        """Listen to tray icon About action and send the signal to About
        dialog.
        """
        logging.info("Show About dialog")
        about_dialog = AboutDialog(self, SAFE_EYES_VERSION)

        if activation_token is not None:
            about_dialog.set_startup_id(activation_token)

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
        self.persist_session()

        self.release()

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
        self._settings_dialog = None

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

        # Restart the core and initialize the components
        self.config = config
        self.safe_eyes_core.initialize(config)
        self.break_screen.initialize(config)

        try:
            self.plugins_manager.reload(self.context, self.config)
        except RequiredPluginException as e:
            self.show_required_plugin_dialog(e)
            return

        if set_active:
            self.active = True

        if self.active and self.safe_eyes_core.has_breaks():
            self.safe_eyes_core.start()
            self.plugins_manager.start()

    def enable_safeeyes(self, scheduled_next_break_time=-1):
        """Listen to tray icon enable action and send the signal to core."""
        if (
            not self.required_plugin_dialog_active
            and not self.active
            and self.safe_eyes_core.has_breaks()
        ):
            self.active = True
            self.safe_eyes_core.start(scheduled_next_break_time)
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

    def take_break(self, break_type: typing.Optional[BreakType] = None) -> None:
        """Take a break now."""
        self.safe_eyes_core.take_break(break_type)

    def status(self):
        """Return the status of Safe Eyes."""
        return self._status

    def persist_session(self):
        """Save the session object to the session file."""
        if self.config.get("persist_state"):
            utility.write_json(utility.SESSION_FILE_PATH, self.context["session"])
        else:
            utility.delete(utility.SESSION_FILE_PATH)
