#!/usr/bin/env python
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

import datetime
import logging

from safeeyes import utility
from safeeyes.breaks.store import BreaksStore
from safeeyes.context import Context
from safeeyes.plugin_utils.manager import PluginManager
from safeeyes.spi.api import BreakAPI
from safeeyes.spi.breaks import BreakType, Break
from safeeyes.spi.state import State
from safeeyes.thread import Heartbeat, ThreadCondition, Timer, worker


class BreakScheduler(BreakAPI):

    def __init__(self, context: Context, heartbeat: Heartbeat, plugin_mgr: PluginManager):
        self.__context = context
        self.__heartbeat = heartbeat
        self.__condition: ThreadCondition = heartbeat.new_condition()
        self.__breaks_store = BreaksStore(context)
        self.__timer = Timer(context, heartbeat, self.__start_break)
        self.__plugins: PluginManager = plugin_mgr

    def start(self):
        if self.__breaks_store.is_empty():
            return
        current_break = self.__breaks_store.get_break()
        current_time = datetime.datetime.now()
        waiting_time = current_break.waiting_time * 60
        next_break_time = current_time + datetime.timedelta(seconds=waiting_time)

        self.schedule(next_break_time)

    def stop(self):
        self.__condition.release_all()
        self.__timer.stop()

    def take_break(self, break_type: BreakType = None):
        if self.__breaks_store.is_empty(break_type):
            return
        with self.__heartbeat.lock:
            self.__context.state = State.BREAK
        self.stop()
        break_obj = self.__breaks_store.get_break(break_type)
        if break_obj is not None:
            self.__take_break(break_obj)

    def has_breaks(self, break_type=None) -> bool:
        return not self.__breaks_store.is_empty(break_type)

    def next_break(self):
        self.__breaks_store.next()
        self.start()

    def skip(self):
        self.__breaks_store.next()
        self.start()

    def schedule(self, next_break_time: datetime):
        if self.__breaks_store.is_empty():
            return
        with self.__heartbeat.lock:
            self.__context.state = State.SCHEDULING
        self.stop()

        next_break = self.__breaks_store.peek()
        short_break_time = next_break_time
        long_break_time = next_break_time
        if next_break.is_long_break():
            short_break_time = next_break_time + datetime.timedelta(
                minutes=self.__breaks_store.peek(BreakType.SHORT).waiting_time)
        else:
            long_break_time = next_break_time + datetime.timedelta(
                minutes=self.__breaks_store.peek(BreakType.LONG).waiting_time)

        self.__context.core_api.set_status(_('Next break at %s') % (utility.format_time(next_break_time)))
        self.__plugins.update_next_break(next_break, short_break_time, long_break_time)

        self.__timer.schedule(next_break_time)

    def __start_break(self):
        print("Starting a break")
        # BreakScheduler always call this method from a separate thread
        with self.__heartbeat.lock:
            self.__context.state = State.PRE_BREAK

        break_obj = self.__breaks_store.get_break()
        # Check if plugins want to cancel this break
        if not self.__plugins.is_break_allowed(break_obj):
            if self.__plugins.is_break_skipped(break_obj):
                # Move to the next break
                logging.info("Break '%s' is skipped by a plugin", break_obj.name)
                self.__breaks_store.next()
                self.start()
                return
            else:
                postpone_time = self.__plugins.get_postpone_time(break_obj)
                if postpone_time <= 0:
                    break_obj.reset_time()
                    postpone_time = break_obj.waiting_time * 60
                logging.info("Break '%s' is postponed for %s seconds by a plugin", break_obj.name, postpone_time)
                next_break_time = datetime.datetime.now() + datetime.timedelta(seconds=postpone_time)
                self.schedule(next_break_time)
                return

        # Send on_pre_break event
        self.__plugins.on_pre_break(break_obj)
        # Wait for pre_break_waiting_time
        pre_break_waiting_time = self.__context.config.get('pre_break_warning_time')
        logging.info("Wait for %d seconds before the break", pre_break_waiting_time)
        self.__condition.hold(pre_break_waiting_time)

        with self.__heartbeat.lock:
            if self.__context.state != State.PRE_BREAK:
                # State changed while waiting
                return
            else:
                self.__context.state = State.BREAK

        self.__take_break(break_obj)

    def __take_break(self, break_obj: Break):
        self.__plugins.on_start_break(break_obj)
        self.__count_down(break_obj)

    @worker
    def __count_down(self, break_obj) -> None:
        countdown = break_obj.duration
        total_break_time = countdown

        while countdown and self.__heartbeat.running and self.__context.state == State.BREAK:
            seconds = total_break_time - countdown
            # TODO: Eliminate the need for countdown in break screen and plugins
            self.__plugins.on_count_down(break_obj, countdown, seconds)
            # Wait for a second
            self.__condition.hold(1)
            countdown -= 1

        # TODO: Replace the hard coded boolean values
        self.__plugins.on_stop_break(break_obj, False, False)
        with self.__heartbeat.lock:
            if self.__context.state != State.BREAK:
                # State changed while counting down
                return

        # Start the next break
        self.next_break()
