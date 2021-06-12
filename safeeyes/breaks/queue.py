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

import random
from typing import Optional, List

from safeeyes.spi.breaks import Break


class Queue:
    """
    A circular queue to store breaks.
    """

    def __init__(self, random_queue: bool):
        """
        Create an empty queue.
        random_queue: make this queue to shuffle itself
        """
        self.__values: List[Break] = []
        self.__index: int = 0
        self.__random: bool = random_queue
        self.__first_peek = True
        self.__first_next = True

    def is_empty(self) -> bool:
        """
        Return true if the queue is empty, otherwise false.
        """
        return len(self.__values) == 0

    def add(self, break_obj: Break) -> None:
        """
        Add the break to the queue.
        """
        self.__values.append(break_obj)

    def peek(self) -> Optional[Break]:
        """
        Return the current value if the queue is not empty.
        """
        if self.__first_peek:
            self.__first_peek = False
            if self.__random:
                self.shuffle()

        if self.__index < len(self.__values):
            return self.__values[self.__index]
        return None

    def next(self) -> Optional[Break]:
        """
        Move to the next item in the queue.
        """
        if self.__first_next:
            self.__first_next = False
            self.__first_peek = False
            return self.peek()

        if self.__index == (len(self.__values) - 1) and self.__random:
            # Starting a new cycle. If required, shuffle the queue next time.
            self.shuffle()

        self.__index = (self.__index + 1) % len(self.__values)

        return self.peek()

    def reset(self) -> None:
        """
        Reset all breaks stored in this queue.
        """
        for break_object in self.__values:
            break_object.reset_time()

    def shuffle(self) -> None:
        """
        Shuffle the queue.
        """
        random.shuffle(self.__values)
