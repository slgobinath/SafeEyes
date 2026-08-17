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
import typing

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio
from safeeyes import utility

context = None
skip_break_window_classes: list[str] = []
take_break_window_classes: list[str] = []
unfullscreen_allowed = True
dnd_while_on_battery = False
ignored_inhibitor_apps: set[str] = set()
_kde_warning_logged = False


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

    import Xlib

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


def get_active_inhibitors() -> typing.Optional[list[tuple[str, str, int]]]:
    """Query GNOME SessionManager for active inhibitors.

    Returns list of (app_id, reason, flags) tuples.
    Returns None on error (callers should handle this as a failure, not empty).
    """
    try:
        session_proxy = Gio.DBusProxy.new_for_bus_sync(
            bus_type=Gio.BusType.SESSION,
            flags=Gio.DBusProxyFlags.NONE,
            info=None,
            name="org.gnome.SessionManager",
            object_path="/org/gnome/SessionManager",
            interface_name="org.gnome.SessionManager",
            cancellable=None,
        )
        inhibitors_variant = session_proxy.call_sync(
            "GetInhibitors",
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
        inhibitor_paths = inhibitors_variant.unpack()[0]

        result = []
        for inhibitor_path in inhibitor_paths:
            try:
                inhibitor_proxy = Gio.DBusProxy.new_for_bus_sync(
                    bus_type=Gio.BusType.SESSION,
                    flags=Gio.DBusProxyFlags.NONE,
                    info=None,
                    name="org.gnome.SessionManager",
                    object_path=inhibitor_path,
                    interface_name="org.gnome.SessionManager.Inhibitor",
                    cancellable=None,
                )
                app_id = inhibitor_proxy.call_sync(
                    "GetAppId", None, Gio.DBusCallFlags.NONE, -1, None
                ).unpack()[0]
                reason = inhibitor_proxy.call_sync(
                    "GetReason", None, Gio.DBusCallFlags.NONE, -1, None
                ).unpack()[0]
                flags = inhibitor_proxy.call_sync(
                    "GetFlags", None, Gio.DBusCallFlags.NONE, -1, None
                ).unpack()[0]
                result.append((app_id, reason, flags))
            except Exception:
                logging.warning(
                    "Failed to query inhibitor at %s, skipping",
                    inhibitor_path,
                )
                continue
        return result
    except Exception:
        logging.warning("Failed to enumerate inhibitors")
        return None


def is_idle_inhibited_gnome():
    """GNOME Shell doesn't work with wlrctl, and there is no way to enumerate
    fullscreen windows, but GNOME does expose whether idle actions like
    starting a screensaver are inhibited, which is a close approximation if not
    a better metric.

    When ignored_inhibitor_apps is configured, enumerates individual inhibitors
    and filters out ignored ones, so breaks can proceed when only ignored apps
    (e.g. Caffeine) are inhibiting idle.
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
    is_inhibited = bool(result & 0b1000)

    if not is_inhibited:
        return False

    # Fast path: no exceptions configured, preserve current behavior
    if not ignored_inhibitor_apps:
        return True

    # Slow path: enumerate inhibitors, filter out ignored ones
    inhibitors = get_active_inhibitors()
    if inhibitors is None:
        logging.warning(
            "Failed to enumerate inhibitors, falling back to bitfield result"
        )
        return True

    for app_id, reason, flags in inhibitors:
        logging.debug("Found inhibitor: %s (flags: %d)", app_id.lower(), flags)

        # Only care about idle inhibitors (fourth bit)
        if not (flags & 0b1000):
            continue

        if app_id.lower() in ignored_inhibitor_apps:
            logging.debug(
                "Ignoring idle inhibitor: %s (in ignored list)", app_id.lower()
            )
            continue

        # Found a non-ignored idle inhibitor
        logging.debug("Non-ignored idle inhibitor found: %s", app_id.lower())
        return True

    # All idle inhibitors were in the ignored list (or enumeration failed)
    logging.debug("All idle inhibitors are in ignored list, proceeding with break")
    return False


def is_idle_inhibited_kde() -> bool:
    """KDE Plasma doesn't work with wlrctl, and there is no way to enumerate
    fullscreen windows, but KDE does expose a non-standard Inhibited property on
    org.freedesktop.Notifications, which does communicate the Do Not Disturb status
    on KDE.
    This is also only an approximation, but comes pretty close.

    Note: ignored_inhibitor_apps is not supported on KDE as there is no
    per-inhibitor enumeration API available.
    """
    global _kde_warning_logged

    if ignored_inhibitor_apps and not _kde_warning_logged:
        logging.warning(
            "ignored_inhibitor_apps is not supported on KDE, ignoring setting"
        )
        _kde_warning_logged = True

    dbus_proxy = Gio.DBusProxy.new_for_bus_sync(
        bus_type=Gio.BusType.SESSION,
        flags=Gio.DBusProxyFlags.NONE,
        info=None,
        name="org.freedesktop.Notifications",
        object_path="/org/freedesktop/Notifications",
        interface_name="org.freedesktop.Notifications",
        cancellable=None,
    )
    prop = dbus_proxy.get_cached_property("Inhibited")

    if prop is None:
        return False

    result = prop.unpack()

    return result


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
    global ignored_inhibitor_apps
    global _kde_warning_logged
    logging.debug("Initialize Skip Fullscreen plugin")
    _kde_warning_logged = False
    context = ctx
    skip_break_window_classes = _normalize_window_classes(
        plugin_config["skip_break_windows"]
    )
    take_break_window_classes = _normalize_window_classes(
        plugin_config["take_break_windows"]
    )
    unfullscreen_allowed = plugin_config["unfullscreen"]
    dnd_while_on_battery = plugin_config["while_on_battery"]
    ignored_inhibitor_apps = set(
        _parse_space_separated_list(plugin_config.get("ignored_inhibitor_apps", ""))
    )


def _parse_space_separated_list(value: str) -> list[str]:
    """Parse a space-separated string into a lowercased list."""
    return [w.lower() for w in value.split()]


def _normalize_window_classes(classes_as_str: str) -> list[str]:
    return _parse_space_separated_list(classes_as_str)


def __should_skip_break(pre_break: bool) -> bool:
    if utility.IS_WAYLAND:
        if utility.DESKTOP_ENVIRONMENT == "gnome":
            skip_break = is_idle_inhibited_gnome()
        elif utility.DESKTOP_ENVIRONMENT == "kde":
            skip_break = is_idle_inhibited_kde()
        else:
            skip_break = is_active_window_skipped_wayland(pre_break)
    else:
        skip_break = is_active_window_skipped_xorg(pre_break)
    if dnd_while_on_battery and not skip_break:
        skip_break = is_on_battery()

    if skip_break:
        logging.info("Skipping break due to donotdisturb")

    return skip_break


def on_pre_break(break_obj):
    """Lifecycle method executes before the pre-break period."""
    return __should_skip_break(pre_break=True)


def on_start_break(break_obj):
    """Lifecycle method executes just before the break."""
    return __should_skip_break(pre_break=False)
