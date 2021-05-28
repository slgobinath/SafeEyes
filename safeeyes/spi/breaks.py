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

from enum import Enum
from typing import List, Optional


class BreakType(Enum):
    """
    Type of Safe Eyes breaks.
    """
    SHORT = 1
    LONG = 2


class Break:
    """
    An entity class representing breaks.
    """

    def __init__(self, break_type: BreakType,
                 name: str,
                 waiting_time: int,
                 duration: int,
                 image: Optional[str],
                 plugins: List[str]):
        self.type: BreakType = break_type
        self.name: str = name
        self.duration: int = duration
        self.image: Optional[str] = image
        self.plugins: List[str] = plugins
        self.waiting_time: int = waiting_time
        # Keep a copy if the original time to reset the self.time later
        self.__original_time: int = waiting_time

    def __str__(self):
        return 'Break: {{name: "{}", type: {}, duration: {}}}\n'.format(self.name, self.type, self.duration)

    def __repr__(self):
        return str(self)

    def is_long_break(self) -> bool:
        """
        Check whether this break is a long break.
        """
        return self.type == BreakType.LONG

    def is_short_break(self) -> bool:
        """
        Check whether this break is a short break.
        """
        return self.type == BreakType.SHORT

    def is_plugin_enabled(self, plugin_id, is_plugin_enabled) -> bool:
        """
        Check whether this break supports the given plugin.
        """
        if self.plugins:
            return plugin_id in self.plugins
        else:
            return is_plugin_enabled

    def reset_time(self) -> None:
        self.waiting_time = self.__original_time
