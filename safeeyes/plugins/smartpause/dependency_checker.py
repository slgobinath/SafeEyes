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


def validate(plugin_config, plugin_settings):
    command = None
    if utility.DESKTOP_ENVIRONMENT == "gnome" and utility.IS_WAYLAND:
        command = "dbus-send"
    elif utility.DESKTOP_ENVIRONMENT == "sway":
        command = "swayidle"
    else:
        command = "xprintidle"
    if not utility.command_exist(command):
        return _("Please install the command-line tool '%s'") % command
    else:
        return None
