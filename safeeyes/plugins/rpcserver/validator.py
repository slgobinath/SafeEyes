# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2021  Gobinath

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
import socket
from contextlib import closing
from typing import Optional
from xmlrpc.client import ServerProxy

from safeeyes.context import Context
from safeeyes.util.locale import get_text as _


def is_available(port: int) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def validate(ctx: Context, plugin_config: dict, plugin_settings: dict) -> Optional[str]:
    port = int(plugin_settings.get("port", 7200))
    original_port = port
    max_attempts = int(plugin_settings.get("max_attempts", 5))
    i = 0
    while i < max_attempts:
        i += 1
        if is_available(port):
            return None
        else:
            try:
                client = ServerProxy("http://localhost:%d/" % port, allow_none=True)
                if ctx.env.user == client.get_user():
                    # Another Safe Eyes is running under the same user
                    return None
            except BaseException:
                # Port is used by some other process
                port += 1
    return _("Failed to acquire a port between %d and %d") % (original_port, port)
