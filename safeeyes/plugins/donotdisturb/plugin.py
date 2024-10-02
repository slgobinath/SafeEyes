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
Skip Fullscreen plugin skips the break if the active window is fullscreen.
NOTE: Do not remove the unused import 'GdkX11' because it is required in Ubuntu 14.04
"""

import os
import logging
import re
import subprocess

import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk
from gi.repository import GdkX11  # noqa F401
from gi.repository import Gio
from safeeyes import utility

context = None
skip_break_window_classes = []
take_break_window_classes = []
unfullscreen_allowed = True
dnd_while_on_battery = False


def is_active_window_skipped_wayland(pre_break):
    cmdlist = ['wlrctl', 'toplevel', 'find', 'state:fullscreen']
    try:
        process = subprocess.Popen(cmdlist, stdout=subprocess.PIPE)
        process.communicate()[0]
        if process.returncode == 0:
            return True
        elif process.returncode == 1:
            return False
        elif process.returncode == 127:
            logging.warning('Could not find wlrctl needed to detect fullscreen under wayland')
            return False
    except subprocess.CalledProcessError:
        logging.warning('Error in finding full-screen application')
    return False


def is_active_window_skipped_xorg(pre_break):
    """
    Check for full-screen applications.
    This method must be executed by the main thread. If not, it will cause random failure.
    """
    logging.info('Searching for full-screen application')
    screen = Gdk.Screen.get_default()

    active_window = screen.get_active_window()
    if active_window:
        active_xid = str(active_window.get_xid())
        cmdlist = ['xprop', '-root', '-notype', '-id',
                   active_xid, 'WM_CLASS', '_NET_WM_STATE']

        try:
            stdout = subprocess.check_output(cmdlist).decode('utf-8')
        except subprocess.CalledProcessError:
            logging.warning('Error in finding full-screen application')
        else:
            if stdout:
                is_fullscreen = 'FULLSCREEN' in stdout
                # Extract the process name
                process_names = re.findall('"(.+?)"', stdout)
                if process_names:
                    process_name = process_names[1].lower()
                    if _window_class_matches(process_name, skip_break_window_classes):
                        return True
                    elif _window_class_matches(process_name, take_break_window_classes):
                        if is_fullscreen and unfullscreen_allowed and not pre_break:
                            try:
                                active_window.unfullscreen()
                            except BaseException as e:
                                logging.error('Error in unfullscreen the window ' + process_name, exc_info=e)
                        return False

                return is_fullscreen

    return False


def is_idle_inhibited_gnome():
    """
    GNOME Shell doesn't work with wlrctl, and there is no way to enumerate
    fullscreen windows, but GNOME does expose whether idle actions like
    starting a screensaver are inhibited, which is a close approximation if
    not a better metric.
    """

    dbus_proxy = Gio.DBusProxy.new_for_bus_sync(
        bus_type=Gio.BusType.SESSION,
        flags=Gio.DBusProxyFlags.NONE,
        info=None,
        name='org.gnome.SessionManager',
        object_path='/org/gnome/SessionManager',
        interface_name='org.gnome.SessionManager',
        cancellable=None,
    )
    result = dbus_proxy.get_cached_property('InhibitedActions').unpack()

    # The result is a bitfield, documented here:
    # https://gitlab.gnome.org/GNOME/gnome-session/-/blob/9aa419397b7f6d42bee6e66cc5c5aad12902fba0/gnome-session/org.gnome.SessionManager.xml#L155
    # The fourth bit indicates that idle is inhibited.
    return bool(result & 0b1000)


def _window_class_matches(window_class: str, classes: list) -> bool:
    return any(map(lambda w: w in classes, window_class.split()))


def is_on_battery():
    """
    Check if the computer is running on battery.
    """
    on_battery = False
    available_power_sources = os.listdir('/sys/class/power_supply')
    logging.info('Looking for battery status in available power sources: %s' % str(
        available_power_sources))
    for power_source in available_power_sources:
        if 'BAT' in power_source:
            # Found battery
            battery_status = os.path.join(
                '/sys/class/power_supply', power_source, 'status')
            if os.path.isfile(battery_status):
                # Additional check to confirm that the status file exists
                try:
                    with open(battery_status, 'r') as status_file:
                        status = status_file.read()
                        if status:
                            on_battery = 'discharging' in status.lower()
                except BaseException:
                    logging.error('Failed to read %s' % battery_status)
            break
    return on_battery


def init(ctx, safeeyes_config, plugin_config):
    global context
    global skip_break_window_classes
    global take_break_window_classes
    global unfullscreen_allowed
    global dnd_while_on_battery
    logging.debug('Initialize Skip Fullscreen plugin')
    context = ctx
    skip_break_window_classes = _normalize_window_classes(plugin_config['skip_break_windows'])
    take_break_window_classes = _normalize_window_classes(plugin_config['take_break_windows'])
    unfullscreen_allowed = plugin_config['unfullscreen']
    dnd_while_on_battery = plugin_config['while_on_battery']


def _normalize_window_classes(classes_as_str: str):
    return [w.lower() for w in classes_as_str.split()]


def on_pre_break(break_obj):
    """
    Lifecycle method executes before the pre-break period.
    """
    if utility.IS_WAYLAND:
        if utility.DESKTOP_ENVIRONMENT == 'gnome':
            skip_break = is_idle_inhibited_gnome()
        else:
            skip_break = is_active_window_skipped_wayland(True)
    else:
        skip_break = is_active_window_skipped_xorg(True)
    if dnd_while_on_battery and not skip_break:
        skip_break = is_on_battery()
    return skip_break


def on_start_break(break_obj):
    """
    Lifecycle method executes just before the break.
    """
    if utility.IS_WAYLAND:
        if utility.DESKTOP_ENVIRONMENT == 'gnome':
            skip_break = is_idle_inhibited_gnome()
        else:
            skip_break = is_active_window_skipped_wayland(False)
    else:
        skip_break = is_active_window_skipped_xorg(False)
    if dnd_while_on_battery and not skip_break:
        skip_break = is_on_battery()
    return skip_break
