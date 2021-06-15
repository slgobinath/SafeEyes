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
Screensaver plugin locks the desktop using native screensaver application, after long breaks.
"""

import logging
import os
from typing import Optional, List

import gi

from safeeyes import utility
from safeeyes.context import Context
from safeeyes.env import system
from safeeyes.spi.breaks import Break
from safeeyes.spi.plugin import TrayAction

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class Screensaver:
    def __init__(self, ctx: Context, config: dict):
        self.min_seconds: int = config["min_seconds"]
        self.__tray_icon_path: str = os.path.join(config["path"], "resource/lock.png")
        self.__command: List[str] = config["command"].split() if config[
            "command"] else Screensaver.__lock_screen_command(ctx.env.name)
        self.__lock_required = False

    def reset(self) -> None:
        self.__lock_required = False

    def lock_later(self) -> None:
        self.__lock_required = True

    def lock_if_required(self) -> None:
        if self.__command is not None and self.__lock_required:
            system.execute(self.__command)

    def is_enabled(self) -> bool:
        return self.__command is not None

    @staticmethod
    def __lock_screen_command(desktop: str):
        """
        Function tries to detect the screensaver command based on the current environment
        Possible results:
            Gnome, Unity, Budgie:		["gnome-screensaver-command", "--lock"]
            Cinnamon:					["cinnamon-screensaver-command", "--lock"]
            Pantheon, LXDE:				["light-locker-command", "--lock"]
            Mate:						["mate-screensaver-command", "--lock"]
            KDE:						["qdbus", "org.freedesktop.ScreenSaver", "/ScreenSaver", "Lock"]
            XFCE:						["xflock4"]
            Otherwise:					None
        """
        if desktop is not None:
            if desktop == "xfce" and utility.command_exist("xflock4"):
                return ["xflock4"]
            elif desktop == "cinnamon" and utility.command_exist("cinnamon-screensaver-command"):
                return ["cinnamon-screensaver-command", "--lock"]
            elif (desktop == "pantheon" or desktop == "lxde") and utility.command_exist("light-locker-command"):
                return ["light-locker-command", "--lock"]
            elif desktop == "mate" and utility.command_exist("mate-screensaver-command"):
                return ["mate-screensaver-command", "--lock"]
            elif desktop == "kde":
                return ["qdbus", "org.freedesktop.ScreenSaver", "/ScreenSaver", "Lock"]
            elif desktop in ["gnome", "unity", "budgie-desktop"]:
                if utility.command_exist("gnome-screensaver-command"):
                    return ["gnome-screensaver-command", "--lock"]
                # From Gnome 3.8 no gnome-screensaver-command
                return ["dbus-send", "--type=method_call", "--dest=org.gnome.ScreenSaver", "/org/gnome/ScreenSaver",
                        "org.gnome.ScreenSaver.Lock"]
        return None


screensaver: Screensaver
tray_icon_path = None


def init(ctx: Context, plugin_config: dict) -> None:
    """
    Initialize the screensaver plugin.
    """
    logging.info("Screensaver: initialize the plugin")
    global screensaver
    global tray_icon_path
    screensaver = Screensaver(ctx, plugin_config)
    tray_icon_path = os.path.join(plugin_config["path"], "resource/lock.png")


def on_start_break(break_obj: Break) -> None:
    """
    Determine the break type and only if it is a long break, enable the lock_screen flag.
    """
    screensaver.reset()


def on_count_down(break_obj: Break, countdown: int, seconds: int) -> None:
    """
    Keep track of seconds passed from the beginning of long break.
    """
    if break_obj.is_long_break() and seconds >= screensaver.min_seconds:
        screensaver.lock_later()


def on_stop_break(break_obj: Break, skipped: bool, postponed: bool) -> None:
    """
    Lock the screen after a long break if the user has not skipped within min_seconds.
    """
    screensaver.lock_if_required()


def get_tray_action(break_obj: Break) -> Optional[TrayAction]:
    if screensaver.is_enabled():
        return TrayAction.build("Lock screen",
                                tray_icon_path,
                                Gtk.STOCK_DIALOG_AUTHENTICATION,
                                screensaver.lock_later)
    else:
        return None
