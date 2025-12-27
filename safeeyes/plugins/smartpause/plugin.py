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
import logging
import typing

from safeeyes.model import State
from safeeyes.context import Context

from .interface import IdleMonitorInterface
from .gnome_dbus import IdleMonitorGnomeDBus
from .swayidle import IdleMonitorSwayidle
from .x11 import IdleMonitorX11

"""
Safe Eyes smart pause plugin
"""

context: Context
idle_time: float = 0
enable_safeeyes = None
disable_safeeyes = None
postpone: typing.Optional[typing.Callable[[int], None]] = None
smart_pause_activated = False
idle_start_time: typing.Optional[datetime.datetime] = None
next_break_time: typing.Optional[datetime.datetime] = None
short_break_interval: int = 0
postpone_if_active: bool = False

is_wayland_and_gnome = False
use_swayidle = False
use_ext_idle_notify = False

idle_monitor: typing.Optional[IdleMonitorInterface] = None
idle_monitor_unsupported: bool = False

idle_monitor_is_pre_break: bool = False
pre_break_idle_start_time: typing.Optional[datetime.datetime] = None

# this is hardcoded currently
pre_break_postpone_idle_time: int = 2


def _on_idle() -> None:
    global smart_pause_activated
    global idle_start_time

    if context["state"] == State.WAITING:
        smart_pause_activated = True
        idle_start_time = datetime.datetime.now() - datetime.timedelta(
            seconds=idle_time
        )
        logging.info("Pause Safe Eyes due to system idle")
        disable_safeeyes(None, True)  # type: ignore[misc]


def _on_resumed() -> None:
    global smart_pause_activated
    global idle_start_time

    if context["state"] == State.RESTING and idle_start_time is not None:
        logging.info("Resume Safe Eyes due to user activity")
        smart_pause_activated = False
        idle_period = datetime.datetime.now() - idle_start_time
        idle_seconds = idle_period.total_seconds()
        context["idle_period"] = idle_seconds
        if idle_seconds < short_break_interval:
            # Credit back the idle time
            if next_break_time is not None:
                # This method runs in a thread since the start.
                # It may run before next_break is initialized in the
                # update_next_break method
                next_break = next_break_time + idle_period
                enable_safeeyes(next_break.timestamp())  # type: ignore[misc]
            else:
                enable_safeeyes()  # type: ignore[misc]
        else:
            # User is idle for more than the time between two breaks
            enable_safeeyes()  # type: ignore[misc]


def _on_idle_pre_break() -> None:
    global pre_break_idle_start_time

    logging.debug("idled before break")
    pre_break_idle_start_time = datetime.datetime.now() - datetime.timedelta(
        seconds=pre_break_postpone_idle_time
    )


def _on_resumed_pre_break() -> None:
    global pre_break_idle_start_time

    logging.debug("resumed before break")
    pre_break_idle_start_time = None


def init(ctx, safeeyes_config, plugin_config) -> None:
    """Initialize the plugin."""
    global context
    global enable_safeeyes
    global disable_safeeyes
    global postpone
    global idle_time
    global short_break_interval
    global postpone_if_active
    global is_wayland_and_gnome
    global use_swayidle
    global use_ext_idle_notify
    logging.debug("Initialize Smart Pause plugin")
    context = ctx
    enable_safeeyes = context["api"]["enable_safeeyes"]
    disable_safeeyes = context["api"]["disable_safeeyes"]
    postpone = context["api"]["postpone"]
    idle_time = plugin_config["idle_time"]
    postpone_if_active = plugin_config["postpone_if_active"]
    short_break_interval = (
        safeeyes_config.get("short_break_interval") * 60
    )  # Convert to seconds
    is_wayland_and_gnome = context["desktop"] == "gnome" and context["is_wayland"]
    use_swayidle = context["desktop"] == "sway"
    use_ext_idle_notify = (
        context["is_wayland"] and not use_swayidle and not is_wayland_and_gnome
    )

    if idle_monitor is not None and idle_monitor.is_monitor_running():
        idle_monitor.configuration_changed(_on_idle, _on_resumed, idle_time)


def on_start() -> None:
    """Start the platform idle monitor."""
    global idle_time
    global idle_monitor
    global idle_monitor_unsupported

    if idle_monitor_unsupported:
        # Don't try and start again if we failed in the past
        return

    if idle_monitor is None:
        if is_wayland_and_gnome:
            idle_monitor = IdleMonitorGnomeDBus()
        elif use_swayidle:
            idle_monitor = IdleMonitorSwayidle()
        elif use_ext_idle_notify:
            from .ext_idle_notify import IdleMonitorExtIdleNotify

            idle_monitor = IdleMonitorExtIdleNotify()
        else:
            idle_monitor = IdleMonitorX11()

        try:
            idle_monitor.init()
        except BaseException as e:
            logging.warning("Unable to get idle time, idle monitor not supported.")
            logging.warning(str(e))
            idle_monitor.stop()
            idle_monitor = None
            idle_monitor_unsupported = True

    if idle_monitor is not None:
        if not idle_monitor.is_monitor_running():
            logging.debug("Start Smart Pause plugin")
            try:
                idle_monitor.start_monitor(_on_idle, _on_resumed, idle_time)
            except BaseException as e:
                logging.warning("Unable to get idle time, idle monitor not supported.")
                logging.warning(str(e))
                idle_monitor.stop_monitor()
                idle_monitor.stop()
                idle_monitor = None
                idle_monitor_unsupported = True


def on_stop() -> None:
    """Stop the platform idle monitor."""
    global idle_monitor
    global smart_pause_activated

    if smart_pause_activated:
        # Safe Eyes is stopped due to system idle
        smart_pause_activated = False
        return
    logging.debug("Stop Smart Pause plugin")

    if idle_monitor is not None:
        if idle_monitor.is_monitor_running():
            idle_monitor.stop_monitor()


def update_next_break(break_obj, dateTime) -> None:
    """Update the next break time."""
    global next_break_time
    next_break_time = dateTime


def on_pre_break(break_obj) -> None:
    """Executes at the start of the prepare time for a break."""
    global postpone_if_active
    global idle_monitor_is_pre_break
    global idle_monitor

    if idle_monitor is not None:
        if postpone_if_active:
            logging.debug("Enabling pre-break idle monitor")
            idle_monitor.configuration_changed(
                _on_idle_pre_break,
                _on_resumed_pre_break,
                pre_break_postpone_idle_time,
            )
            idle_monitor_is_pre_break = True
        else:
            # Stop during the pre break
            logging.debug("Stop idle monitor during break")
            idle_monitor.stop_monitor()


def on_start_break(break_obj) -> None:
    """Lifecycle method executes just before the break."""
    global postpone_if_active
    global idle_monitor_is_pre_break
    global pre_break_idle_start_time

    if postpone_if_active:
        if idle_monitor_is_pre_break:
            # Postpone this break if the user is active
            system_idle_time = 0.0
            if pre_break_idle_start_time is not None:
                idle_period = datetime.datetime.now() - pre_break_idle_start_time
                system_idle_time = idle_period.total_seconds()

            if system_idle_time < pre_break_postpone_idle_time:
                logging.debug("User is not idle, postponing")
                postpone(pre_break_postpone_idle_time)  # type: ignore[misc]
                return

            logging.debug(f"User was idle for {system_idle_time}, time for the break")

    if idle_monitor is not None:
        # Stop during the break
        # The normal monitor should no longer be running here - try stopping anyways
        if idle_monitor.is_monitor_running():
            logging.debug("Start break, disable the pre-break idle monitor")
            idle_monitor.stop_monitor()
        # We stopped, the pre_break monitor is no longer running
        idle_monitor_is_pre_break = False
        pre_break_idle_start_time = None


def on_stop_break() -> None:
    """Lifecycle method executes after the break."""
    global idle_monitor_is_pre_break
    global postpone_if_active

    if idle_monitor is not None:
        if not idle_monitor.is_monitor_running():
            logging.debug("Break is done, reenable idle monitor")
            idle_monitor.start_monitor(_on_idle, _on_resumed, idle_time)


def disable() -> None:
    """SmartPause plugin was active earlier but now user has disabled it."""
    global idle_monitor

    # Remove the idle_period
    context.pop("idle_period", None)

    if idle_monitor is not None:
        idle_monitor.stop()
        idle_monitor = None


def on_exit() -> None:
    """Safe Eyes is exiting."""
    global idle_monitor

    if idle_monitor is not None:
        idle_monitor.stop()
        idle_monitor = None
