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
Safe Eyes smart pause plugin
"""

import datetime
import logging
import subprocess
import re
from typing import Optional, Callable

import xcffib
import xcffib.xproto
import xcffib.screensaver

from safeeyes import Utility
from safeeyes.model import State
from .interface import IdleTimeInterface

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib


context: Optional[dict] = None
active = False
idle_time = 0
enable_safe_eyes: Optional[Callable[[Optional[int]], None]] = None
disable_safe_eyes: Optional[Callable[[Optional[str]], None]] = None
postpone: Optional[Callable[[Optional[int]], None]] = None
smart_pause_activated = False
idle_start_time: Optional[datetime.datetime] = None
next_break_time: Optional[datetime.datetime] = None
next_break_duration = 0
break_interval = 0
waiting_time = 2
interpret_idle_as_break = False
postpone_if_active = False
idle_checker: Optional[IdleTimeInterface] = None
_timer_event_id: Optional[int] = None


class GnomeWaylandIdleTime(IdleTimeInterface):
    """
    Determine system idle time in seconds, specifically for gnome with wayland.
    https://unix.stackexchange.com/a/492328/222290
    """

    @classmethod
    def is_applicable(cls, ctx) -> bool:
        if ctx['desktop'] == 'gnome' and ctx['is_wayland']:
            # ? Might work in all Gnome environments running Mutter whether they're Wayland or X?
            return Utility.command_exist("dbus-send")

        return False

    def idle_seconds(self):
        # noinspection PyBroadException
        try:
            output = subprocess.check_output([
                'dbus-send',
                '--print-reply',
                '--dest=org.gnome.Mutter.IdleMonitor',
                '/org/gnome/Mutter/IdleMonitor/Core',
                'org.gnome.Mutter.IdleMonitor.GetIdletime'
            ])
            return int(re.search(rb'\d+$', output).group(0)) / 1000
        except Exception:
            logging.warning("Failed to get system idle time for gnome/wayland.", exc_info=True)
            return 0

    def destroy(self) -> None:
        pass


class X11IdleTime(IdleTimeInterface):

    def __init__(self):
        self.connection = xcffib.connect()
        self.screensaver_ext = self.connection(xcffib.screensaver.key)

    @classmethod
    def is_applicable(cls, _context) -> bool:
        return True

    def idle_seconds(self):
        # noinspection PyBroadException
        try:
            root_window = self.connection.get_setup().roots[0].root
            query = self.screensaver_ext.QueryInfo(root_window)
            info = query.reply()
            # Convert to seconds
            return info.ms_since_user_input / 1000
        except Exception:
            logging.warning("Failed to get system idle time from XScreenSaver API", exc_info=True)
            return 0

    def destroy(self) -> None:
        self.connection.disconnect()


_idle_checkers = [
    GnomeWaylandIdleTime,
    X11IdleTime
]


def idle_checker_for_platform(ctx) -> Optional[IdleTimeInterface]:
    """
    Create the appropriate idle checker for this context.
    """
    for cls in _idle_checkers:
        if cls.is_applicable(ctx):
            checker = cls()
            logging.debug("Using idle checker %s", checker)
            return checker

    logging.warning("Could not find any appropriate idle checker.")
    return None


def __is_active():
    """
    Function to see if this plugin is active or not.
    """
    return active


def __set_active(is_active):
    """
    Function to change the state of the plugin.
    """
    global active
    active = is_active


def init(ctx, safeeyes_config, plugin_config):
    """
    Initialize the plugin.
    """
    global context
    global enable_safe_eyes
    global disable_safe_eyes
    global postpone
    global idle_time
    global break_interval
    global waiting_time
    global interpret_idle_as_break
    global postpone_if_active
    logging.debug('Initialize Smart Pause plugin')
    context = ctx
    enable_safe_eyes = context['api']['enable_safeeyes']
    disable_safe_eyes = context['api']['disable_safeeyes']
    postpone = context['api']['postpone']
    idle_time = plugin_config['idle_time']
    interpret_idle_as_break = plugin_config['interpret_idle_as_break']
    postpone_if_active = plugin_config['postpone_if_active']
    break_interval = safeeyes_config.get(
        'short_break_interval') * 60  # Convert to seconds
    waiting_time = min(2, idle_time)  # If idle time is 1 sec, wait only 1 sec


def __idle_monitor():
    """
    Check the system idle time and pause/resume Safe Eyes based on it.
    """
    global smart_pause_activated
    global idle_start_time

    if not __is_active():
        return False  # stop the timeout handler.

    system_idle_time = idle_checker.idle_seconds()
    if system_idle_time >= idle_time and context['state'] == State.WAITING:
        smart_pause_activated = True
        idle_start_time = datetime.datetime.now()
        logging.info('Pause Safe Eyes due to system idle')
        disable_safe_eyes(None)
    elif system_idle_time < idle_time and context['state'] == State.STOPPED:
        logging.info('Resume Safe Eyes due to user activity')
        smart_pause_activated = False
        idle_period = (datetime.datetime.now() - idle_start_time)
        idle_seconds = idle_period.total_seconds()
        context['idle_period'] = idle_seconds
        if interpret_idle_as_break and idle_seconds >= next_break_duration:
            # User is idle for break duration and wants to consider it as a break
            enable_safe_eyes()
        elif idle_seconds < break_interval:
            # Credit back the idle time
            next_break = next_break_time + idle_period
            enable_safe_eyes(next_break.timestamp())
        else:
            # User is idle for more than the time between two breaks
            enable_safe_eyes()

    return True  # keep this timeout handler registered.


def on_start():
    """
    Begin polling to check user idle time.
    """
    global idle_checker
    global _timer_event_id

    if __is_active():
        # If SmartPause is already started, do not start it again
        return

    logging.debug('Start Smart Pause plugin')
    idle_checker = idle_checker_for_platform(context)

    __set_active(True)

    # FIXME: need to make sure that this gets updated if the waiting_time config changes
    _timer_event_id = GLib.timeout_add_seconds(waiting_time, __idle_monitor)


def on_stop():
    """
    Stop polling to check user idle time.
    """
    global smart_pause_activated
    global _timer_event_id
    global idle_checker

    if smart_pause_activated:
        # Safe Eyes is stopped due to system idle
        smart_pause_activated = False
        return
    logging.debug('Stop Smart Pause plugin')
    __set_active(False)
    GLib.source_remove(_timer_event_id)
    _timer_event_id = None
    if idle_checker is not None:
        idle_checker.destroy()
        idle_checker = None


def update_next_break(break_obj, break_time):
    """
    Update the next break time.
    """
    global next_break_time
    global next_break_duration
    next_break_time = break_time
    next_break_duration = break_obj.duration


def on_start_break(_break_obj):
    """
    Lifecycle method executes just before the break.
    """
    if postpone_if_active:
        # Postpone this break if the user is active
        system_idle_time = idle_checker.idle_seconds()
        if system_idle_time < 2:
            postpone(2)  # Postpone for 2 seconds


def disable():
    """
    SmartPause plugin was active earlier but now user has disabled it.
    """
    # Remove the idle_period
    context.pop('idle_period', None)
