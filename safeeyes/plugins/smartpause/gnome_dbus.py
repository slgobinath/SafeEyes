# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2025  Mel Dafert <m@dafert.at>

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

import typing

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib


from .interface import IdleMonitorInterface


class IdleMonitorGnomeDBus(IdleMonitorInterface):
    """IdleMonitorInterface implementation for GNOME."""

    dbus_proxy: typing.Optional[Gio.DBusProxy] = None
    idle_watch_id: typing.Optional[int] = None
    active_watch_id: typing.Optional[int] = None

    was_idle: bool = False

    _on_idle: typing.Optional[typing.Callable[[], None]] = None
    _on_resumed: typing.Optional[typing.Callable[[], None]] = None

    def init(self) -> None:
        if self.dbus_proxy is None:
            self.dbus_proxy = Gio.DBusProxy.new_for_bus_sync(
                bus_type=Gio.BusType.SESSION,
                flags=Gio.DBusProxyFlags.NONE,
                info=None,
                name="org.gnome.Mutter.IdleMonitor",
                object_path="/org/gnome/Mutter/IdleMonitor/Core",
                interface_name="org.gnome.Mutter.IdleMonitor",
                cancellable=None,
            )

            self.dbus_proxy.connect("g-signal", self._handle_proxy_signal)

    def start_monitor(
        self,
        on_idle: typing.Callable[[], None],
        on_resumed: typing.Callable[[], None],
        idle_time: float,
    ) -> None:
        """Start watching for idling.

        This is run on the main thread, and should not block.
        """
        if self.is_monitor_running():
            self.stop()

        self._on_idle = on_idle
        self._on_resumed = on_resumed
        # NOTE: this is currently somewhat buggy, actually
        # This does not start counting the idle time when the watch is added
        # if the user was idle for more than `idle_time` s, this will fire immediately
        # This is not a big issue, but does mean that it might pause safeeyes right
        # after a break finishes
        self.idle_watch_id = self.dbus_proxy.AddIdleWatch(  # type: ignore[union-attr]
            "(t)", idle_time * 1000
        )

    def _handle_proxy_signal(
        self,
        dbus_proxy: Gio.DBusProxy,
        sender_name: typing.Optional[str],
        signal_name: str,
        parameters: GLib.Variant,
    ) -> None:
        if signal_name == "WatchFired":
            watch_id: int
            (watch_id,) = parameters  # type: ignore[misc]

            if watch_id == self.idle_watch_id:
                if self.active_watch_id is not None:
                    dbus_proxy.RemoveWatch("(u)", self.active_watch_id)  # type: ignore[attr-defined]
                self.active_watch_id = dbus_proxy.AddUserActiveWatch("()")  # type: ignore[attr-defined]
                if not self.was_idle:
                    self.was_idle = True
                    if self._on_idle:
                        self._on_idle()

            if self.active_watch_id is not None and watch_id == self.active_watch_id:
                self.active_watch_id = None
                if self.was_idle:
                    self.was_idle = False
                    if self._on_resumed:
                        self._on_resumed()

    def is_monitor_running(self) -> bool:
        return self.idle_watch_id is not None

    def stop_monitor(self) -> None:
        """Stop watching for idling.

        This is run on the main thread. It may block a short time for cleanup.
        """
        if self.is_monitor_running() and self.dbus_proxy is not None:
            self.dbus_proxy.RemoveWatch("(u)", self.idle_watch_id)  # type: ignore[attr-defined]
            self.idle_watch_id = None

            if self.active_watch_id is not None:
                self.dbus_proxy.RemoveWatch("(u)", self.active_watch_id)  # type: ignore[attr-defined]
                self.active_watch_id = None

        self.was_idle = False

    def stop(self) -> None:
        self.dbus_proxy = None
