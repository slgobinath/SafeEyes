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

from safeeyes import utility
from safeeyes.model import PluginDependency

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio


def validate(plugin_config, plugin_settings):
    dbus_proxy = Gio.DBusProxy.new_for_bus_sync(
        bus_type=Gio.BusType.SESSION,
        flags=Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
        info=None,
        name="org.freedesktop.DBus",
        object_path="/org/freedesktop/DBus",
        interface_name="org.freedesktop.DBus",
        cancellable=None,
    )

    if dbus_proxy.NameHasOwner("(s)", "org.kde.StatusNotifierWatcher"):
        return None
    else:
        return PluginDependency(
            message=_(
                "Please install service providing tray icons for your desktop"
                " environment."
            ),
            link="https://github.com/slgobinath/SafeEyes/wiki/How-to-install-backend-for-Safe-Eyes-tray-icon",
            retryable=True,
        )

    command = None
    if utility.IS_WAYLAND:
        if utility.DESKTOP_ENVIRONMENT == "gnome":
            return None
        command = "wlrctl"
    else:
        command = "xprop"
    if not utility.command_exist(command):
        return _("Please install the command-line tool '%s'") % command
    else:
        return None
