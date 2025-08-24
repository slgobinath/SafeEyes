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
"""Screensaver plugin locks the desktop using native screensaver application,
after long breaks.
"""

import logging
import os
import typing

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio

from safeeyes import utility
from safeeyes.model import TrayAction

context = None
is_long_break: bool = False
user_locked_screen = False
lock_screen_command: typing.Union[list[str], typing.Callable[[], None], None] = None
min_seconds = 0
seconds_passed = 0
tray_icon_path = None
icon_lock_later_path = None


def __lock_screen_command() -> typing.Union[list[str], typing.Callable[[], None], None]:
    """Function tries to detect the screensaver command based on the current
    envinroment.

    Returns either a command to execute or function to call.

    Possible results:
        Modern GNOME:               DBus: org.gnome.ScreenSaver.Lock
        Old Gnome, Unity, Budgie:	['gnome-screensaver-command', '--lock']
        Cinnamon:					['cinnamon-screensaver-command', '--lock']
        Pantheon, LXDE:				['light-locker-command', '--lock']
        Mate:						['mate-screensaver-command', '--lock']
        KDE:						DBus: org.freedesktop.ScreenSaver.Lock
        XFCE:						['xflock4']
        Otherwise:					None
    """
    desktop_session = os.environ.get("DESKTOP_SESSION")
    current_desktop = os.environ.get("XDG_CURRENT_DESKTOP")
    if desktop_session is not None:
        desktop_session = desktop_session.lower()
        if (
            "xfce" in desktop_session
            or desktop_session.startswith("xubuntu")
            or (current_desktop is not None and "xfce" in current_desktop)
        ) and utility.command_exist("xflock4"):
            return ["xflock4"]
        elif desktop_session == "cinnamon" and utility.command_exist(
            "cinnamon-screensaver-command"
        ):
            # This calls org.cinnamon.ScreenSaver.Lock internally
            return ["cinnamon-screensaver-command", "--lock"]
        elif (
            desktop_session == "pantheon" or desktop_session.startswith("lubuntu")
        ) and utility.command_exist("light-locker-command"):
            return ["light-locker-command", "--lock"]
        elif desktop_session == "mate" and utility.command_exist(
            "mate-screensaver-command"
        ):
            # This calls org.mate.ScreenSaver.Lock internally
            # However, it warns not to rely on that
            return ["mate-screensaver-command", "--lock"]
        elif (
            desktop_session == "kde"
            or "plasma" in desktop_session
            or desktop_session.startswith("kubuntu")
            or os.environ.get("KDE_FULL_SESSION") == "true"
        ):
            # Note that this is unfortunately a non-standard KDE extension.
            # See https://gitlab.gnome.org/GNOME/gnome-settings-daemon/-/issues/632
            # for details.
            return lambda: __lock_screen_dbus(
                destination="org.freedesktop.ScreenSaver",
                path="/ScreenSaver",
                method="Lock",
            )
        elif (
            desktop_session in ["gnome", "unity", "budgie-desktop"]
            or desktop_session.startswith("ubuntu")
            or desktop_session.startswith("gnome")
        ):
            if utility.command_exist("gnome-screensaver-command"):
                return ["gnome-screensaver-command", "--lock"]
            # From Gnome 3.8 no gnome-screensaver-command
            return lambda: __lock_screen_dbus(
                destination="org.gnome.ScreenSaver",
                path="/org/gnome/ScreenSaver",
                method="Lock",
            )
        elif gd_session := os.environ.get("GNOME_DESKTOP_SESSION_ID"):
            if "deprecated" not in gd_session and utility.command_exist(
                "gnome-screensaver-command"
            ):
                # Gnome 2
                return ["gnome-screensaver-command", "--lock"]
    return None


def __lock_screen_dbus(destination: str, path: str, method: str) -> None:
    """This assumes that the interface is the same as the destination."""
    dbus_proxy = Gio.DBusProxy.new_for_bus_sync(
        bus_type=Gio.BusType.SESSION,
        flags=Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
        info=None,
        name=destination,
        object_path=path,
        interface_name=destination,
    )

    dbus_proxy.call_sync(method, None, Gio.DBusCallFlags.NONE, -1)


def __lock_screen_later():
    global user_locked_screen
    user_locked_screen = True


def __lock_screen_now() -> None:
    global lock_screen_command

    if lock_screen_command is None:
        return

    if isinstance(lock_screen_command, list):
        utility.execute_command(lock_screen_command)
    else:
        lock_screen_command()


def init(ctx, safeeyes_config, plugin_config):
    """Initialize the screensaver plugin."""
    global context
    global lock_screen_command
    global min_seconds
    global tray_icon_path
    global icon_lock_later_path
    logging.debug("Initialize Screensaver plugin")
    context = ctx
    min_seconds = plugin_config["min_seconds"]
    tray_icon_path = os.path.join(plugin_config["path"], "resource/lock.png")
    icon_lock_later_path = os.path.join(
        plugin_config["path"], "resource/rotation-lock-symbolic.svg"
    )
    if plugin_config["command"]:
        lock_screen_command = plugin_config["command"].split()
    else:
        lock_screen_command = __lock_screen_command()


def on_start_break(break_obj):
    """Determine the break type and only if it is a long break, enable the
    is_long_break flag.
    """
    global is_long_break
    global seconds_passed
    global user_locked_screen
    user_locked_screen = False
    seconds_passed = 0

    is_long_break = break_obj.is_long_break()


def on_countdown(countdown, seconds):
    """Keep track of seconds passed from the beginning of long break."""
    global seconds_passed
    seconds_passed = seconds


def on_stop_break():
    """Lock the screen after a long break if the user has not skipped within
    min_seconds.
    """
    if user_locked_screen or (is_long_break and seconds_passed >= min_seconds):
        __lock_screen_now()


def get_tray_action(break_obj) -> list[TrayAction]:
    return [
        TrayAction.build(
            "Lock screen now",
            tray_icon_path,
            "system-lock-screen",
            __lock_screen_now,
            single_use=False,
        ),
        TrayAction.build(
            "Lock screen after break",
            icon_lock_later_path,
            "dialog-password",
            __lock_screen_later,
        ),
    ]
