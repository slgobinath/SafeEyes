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

import logging
from typing import Optional

from safeeyes.breaks.queue import Queue
from safeeyes.context import Context, SESSION_KEY_BREAK, SESSION_KEY_BREAK_TYPE
from safeeyes.spi.breaks import Break, BreakType


class BreaksStore:
    def __init__(self, context: Context):
        self.__context: Context = context
        self.__current_break: Optional[Break] = None
        self.__short_break_time = context.config.get('short_break_interval')
        self.__long_break_time = context.config.get('long_break_interval')
        self.__is_random_order = context.config.get('random_order')
        self.__short_queue: Queue = self.__build_shorts()
        self.__long_queue: Queue = self.__build_longs()

        # Restore the last break from session
        self.__restore_last_break(context.session.get(SESSION_KEY_BREAK))

    def get_break(self, break_type=None) -> Optional[Break]:
        if self.__current_break is None:
            self.__current_break = self.next(break_type)
        elif break_type is not None and self.__current_break.type != break_type:
            self.__current_break = self.next(break_type)

        return self.__current_break

    def peek(self, break_type: BreakType = None) -> Optional[Break]:
        """
        Get the next break without moving the pointer to the next break.
        """
        if break_type == BreakType.LONG:
            return self.__long_queue.peek()
        elif break_type == BreakType.SHORT:
            return self.__short_queue.peek()
        else:
            return self.__current_break

    def next(self, break_type=None) -> Optional[Break]:
        """
        Select the next break. If the queue is empty, return None.
        """
        break_obj = None
        if self.is_empty():
            return break_obj

        if self.__short_queue.is_empty():
            break_obj = self.__next_long()
        elif self.__long_queue.is_empty():
            break_obj = self.__next_short()
        elif break_type == BreakType.LONG or self.__long_queue.peek().waiting_time <= self.__short_queue.peek().waiting_time:
            break_obj = self.__next_long()
        else:
            break_obj = self.__next_short()

        break_obj.reset_time()
        self.__current_break = break_obj
        self.__context.session.set(SESSION_KEY_BREAK, self.__current_break.name)

        return break_obj

    def reset(self) -> None:
        """
        Reset break times.
        """
        self.__short_queue.reset()
        self.__long_queue.reset()

    def is_empty(self, break_type=None) -> bool:
        """
        Check if the given break type is empty or not. If the break_type is None, check for both short and long breaks.
        """
        if break_type == BreakType.SHORT:
            return self.__short_queue.is_empty()
        elif break_type == BreakType.LONG:
            return self.__long_queue.is_empty()
        else:
            return self.__short_queue.is_empty() and self.__long_queue.is_empty()

    def __next_short(self) -> Optional[Break]:
        break_obj = self.__short_queue.next()
        if break_obj is not None:
            self.__context.session.set(SESSION_KEY_BREAK_TYPE, BreakType.SHORT)
            # Reduce the waiting time from the next long break
            if not self.__long_queue.is_empty():
                next_long_break = self.__long_queue.peek()
                if next_long_break:
                    next_long_break.waiting_time -= break_obj.waiting_time

        return break_obj

    def __next_long(self) -> Optional[Break]:
        self.__context.session.set(SESSION_KEY_BREAK_TYPE, BreakType.LONG)
        return self.__long_queue.next()

    def __restore_last_break(self, last_break: str) -> None:
        if not self.is_empty() and last_break is not None:
            current_break = self.get_break()
            if last_break != current_break.name:
                next_break = self.next()
                if next_break is not None:
                    while next_break != current_break and next_break.name != last_break:
                        next_break = self.next()

    def __build_shorts(self) -> Queue:
        return BreaksStore.__build_queue(BreakType.SHORT,
                                         self.__context.config.get('short_breaks'),
                                         self.__short_break_time,
                                         self.__context.config.get('short_break_duration'),
                                         self.__is_random_order)

    def __build_longs(self) -> Queue:
        return BreaksStore.__build_queue(BreakType.LONG,
                                         self.__context.config.get('long_breaks'),
                                         self.__long_break_time,
                                         self.__context.config.get('long_break_duration'),
                                         self.__is_random_order)

    @staticmethod
    def __build_queue(break_type: BreakType, break_configs, break_time, break_duration, random_queue) -> Queue:
        """
        Build a queue of breaks. If there are no queues, return an empty queue.
        """
        queue = Queue(random_queue)
        for i, break_config in enumerate(break_configs):
            name = _(break_config['name'])
            duration = break_config.get('duration', break_duration)
            image = break_config.get('image')
            plugins = break_config.get('plugins', None)
            interval = break_config.get('interval', break_time)

            # Validate time value
            if not isinstance(duration, int) or duration <= 0:
                logging.error('Invalid break duration in: ' + str(break_config))
                continue

            break_obj = Break(break_type, name, interval,
                              duration, image, plugins)
            queue.add(break_obj)

        return queue
