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
This module contains the entity classes used by Safe Eyes and its plugins.
"""

from enum import Enum

class Break(object):
    """
    An entity class which represents a break.
    """
    def __init__(self, break_type, name, time, image, plugins):
        self.type = break_type
        self.name = name
        self.time = time
        self.image = image
        self.plugins = plugins

    def __str__(self):
        return 'Break: {{name: "{}", type: {}, time: {}}}\n'.format(self.name, self.type, self.time)

    def __repr__(self):
        return str(self)

    def is_long_break(self):
        """
        Check whether this break is a long break.
        """
        return self.type == BreakType.LONG_BREAK

    def is_short_break(self):
        """
        Check whether this break is a short break.
        """
        return self.type == BreakType.SHORT_BREAK

class BreakType(Enum):
    """
    Type of Safe Eyes breaks.
    """
    SHORT_BREAK = 1
    LONG_BREAK = 2

class State(Enum):
    """
    Possible states of Safe Eyes.
    """
    WAITING = 0,
    PRE_BREAK = 1
    BREAK = 2,
    STOPPED = 3

class EventHook(object):
    """
    Hook to attach and detach listeners to system events.
    """
    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__handlers.remove(handler)
        return self

    def fire(self, *args, **keywargs):
        """
        Fire all listeners attached with.
        """
        for handler in self.__handlers:
            if not handler(*args, **keywargs):
                return False
        return True
