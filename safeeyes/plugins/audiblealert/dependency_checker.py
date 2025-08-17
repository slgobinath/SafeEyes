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

from safeeyes import utility
from safeeyes.translations import translate as _


def validate(plugin_config, plugin_settings):
    commands = ["ffplay", "pw-play"]
    exists = False
    for command in commands:
        if utility.command_exist(command):
            exists = True
            break

    if not exists:
        return _("Please install one of the command-line tools: %s") % ", ".join(
            [f"'{command}'" for command in commands]
        )
    else:
        return None
