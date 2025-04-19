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
"""Skip Fullscreen plugin skips the break if the active window is fullscreen."""

import os
import logging
import subprocess

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio
import Xlib
from safeeyes import utility

context = None
skip_break_window_classes: list[str] = []
take_break_window_classes: list[str] = []
unfullscreen_allowed = True
dnd_while_on_battery = False


def is_active_window_skipped_wayland(pre_break):
    cmdlist = ["wlrctl", "toplevel", "find", "state:fullscreen"]
    try:
        process = subprocess.Popen(cmdlist, stdout=subprocess.PIPE)
        process.communicate()[0]
        if process.returncode == 0:
            return True
        elif process.returncode == 1:
            return False
        elif process.returncode == 127:
            logging.warning(
                "Could not find wlrctl needed to detect fullscreen under wayland"
            )
            return False
    except subprocess.CalledProcessError:
        logging.warning("Error in finding full-screen application")
    return False


def is_active_window_skipped_xorg(pre_break):
    """Check for full-screen applications.

    This method must be executed by the main thread. If not, it will
    cause random failure.
    """
    logging.info("Searching for full-screen application")

    def get_window_property(window, prop, proptype):
        result = window.get_full_property(prop, proptype)
        if result:
            return result.value

        return None

    def get_active_window(x11_display):
        """Get active window using EWMH hints.

        Returns None if there is no active window.
        This always returns None if the window manager does not use EWMH hints.
        However, GTK3 also used this method to get the active window.
        """
        root = x11_display.screen().root
        NET_ACTIVE_WINDOW = x11_display.intern_atom("_NET_ACTIVE_WINDOW")

        active_windows = get_window_property(root, NET_ACTIVE_WINDOW, Xlib.Xatom.WINDOW)
        if active_windows and active_windows[0]:
            active_window = active_windows[0]
            return x11_display.create_resource_object("window", active_window)
        return None

    x11_display = Xlib.display.Display()

    active_window = get_active_window(x11_display)

    if active_window:
        NET_WM_STATE = x11_display.intern_atom("_NET_WM_STATE")
        NET_WM_STATE_FULLSCREEN = x11_display.intern_atom("_NET_WM_STATE_FULLSCREEN")

        props = get_window_property(active_window, NET_WM_STATE, Xlib.Xatom.ATOM)
        is_fullscreen = props and NET_WM_STATE_FULLSCREEN in props.tolist()

        process_names = active_window.get_wm_class()

        if is_fullscreen:
            logging.info("fullscreen window found")

        if process_names:
            process_name = process_names[1].lower()
            if _window_class_matches(process_name, skip_break_window_classes):
                logging.info("found uninterruptible window")
                return True
            elif _window_class_matches(process_name, take_break_window_classes):
                logging.info("found interruptible window")
                if is_fullscreen and unfullscreen_allowed and not pre_break:
                    logging.info("interrupting interruptible window")
                    try:
                        # To change the fullscreen state, we cannot simply set the
                        # property - we must send a ClientMessage event
                        # See https://specifications.freedesktop.org/wm-spec/1.3/ar01s05.html#id-1.6.8
                        root_window = x11_display.screen().root

                        cm_event = Xlib.protocol.event.ClientMessage(
                            window=active_window,
                            client_type=NET_WM_STATE,
                            data=(
                                32,
                                [
                                    0,  # _NET_WM_STATE_REMOVE
                                    NET_WM_STATE_FULLSCREEN,
                                    0,  # other property, must be 0
                                    1,  # source indication
                                    0,  # must be 0
                                ],
                            ),
                        )

                        mask = (
                            Xlib.X.SubstructureRedirectMask
                            | Xlib.X.SubstructureNotifyMask
                        )

                        root_window.send_event(cm_event, event_mask=mask)

                        x11_display.sync()

                    except BaseException as e:
                        logging.error(
                            "Error in unfullscreen the window " + process_name,
                            exc_info=e,
                        )
                return False

        return is_fullscreen

    return False


def is_idle_inhibited_gnome():
    """GNOME Shell doesn't work with wlrctl, and there is no way to enumerate
    fullscreen windows, but GNOME does expose whether idle actions like
    starting a screensaver are inhibited, which is a close approximation if not
    a better metric.
    """
    dbus_proxy = Gio.DBusProxy.new_for_bus_sync(
        bus_type=Gio.BusType.SESSION,
        flags=Gio.DBusProxyFlags.NONE,
        info=None,
        name="org.gnome.SessionManager",
        object_path="/org/gnome/SessionManager",
        interface_name="org.gnome.SessionManager",
        cancellable=None,
    )
    result = dbus_proxy.get_cached_property("InhibitedActions").unpack()

    # The result is a bitfield, documented here:
    # https://gitlab.gnome.org/GNOME/gnome-session/-/blob/9aa419397b7f6d42bee6e66cc5c5aad12902fba0/gnome-session/org.gnome.SessionManager.xml#L155
    # The fourth bit indicates that idle is inhibited.
    return bool(result & 0b1000)


def _window_class_matches(window_class: str, classes: list) -> bool:
    return any(map(lambda w: w in classes, window_class.split()))


def is_on_battery():
    """Check if the computer is running on battery."""
    on_battery = False
    available_power_sources = os.listdir("/sys/class/power_supply")
    logging.info(
        "Looking for battery status in available power sources: %s"
        % str(available_power_sources)
    )
    for power_source in available_power_sources:
        if "BAT" in power_source:
            # Found battery
            battery_status = os.path.join(
                "/sys/class/power_supply", power_source, "status"
            )
            if os.path.isfile(battery_status):
                # Additional check to confirm that the status file exists
                try:
                    with open(battery_status, "r") as status_file:
                        status = status_file.read()
                        if status:
                            on_battery = "discharging" in status.lower()
                except BaseException:
                    logging.error("Failed to read %s" % battery_status)
            break
    return on_battery


def init(ctx, safeeyes_config, plugin_config):
    global context
    global skip_break_window_classes
    global take_break_window_classes
    global unfullscreen_allowed
    global dnd_while_on_battery
    logging.debug("Initialize Skip Fullscreen plugin")
    context = ctx
    skip_break_window_classes = _normalize_window_classes(
        plugin_config["skip_break_windows"]
    )
    take_break_window_classes = _normalize_window_classes(
        plugin_config["take_break_windows"]
    )
    unfullscreen_allowed = plugin_config["unfullscreen"]
    dnd_while_on_battery = plugin_config["while_on_battery"]


def _normalize_window_classes(classes_as_str: str):
    return [w.lower() for w in classes_as_str.split()]


def on_pre_break(break_obj):
    """Lifecycle method executes before the pre-break period."""
    if utility.IS_WAYLAND:
        if utility.DESKTOP_ENVIRONMENT == "gnome":
            skip_break = is_idle_inhibited_gnome()
        else:
            skip_break = is_active_window_skipped_wayland(True)
    else:
        skip_break = is_active_window_skipped_xorg(True)
    if dnd_while_on_battery and not skip_break:
        skip_break = is_on_battery()
    return skip_break


def on_start_break(break_obj):
    """Lifecycle method executes just before the break."""
    if utility.IS_WAYLAND:
        if utility.DESKTOP_ENVIRONMENT == "gnome":
            skip_break = is_idle_inhibited_gnome()
        else:
            skip_break = is_active_window_skipped_wayland(False)
    else:
        skip_break = is_active_window_skipped_xorg(False)
    if dnd_while_on_battery and not skip_break:
        skip_break = is_on_battery()
    return skip_break
