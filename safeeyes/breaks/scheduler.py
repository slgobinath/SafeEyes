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
from typing import Optional

from safeeyes import utility
from safeeyes.breaks.store import BreaksStore
from safeeyes.context import Context
from safeeyes.plugin_utils.manager import PluginManager
from safeeyes.spi.api import BreakAPI
from safeeyes.spi.breaks import BreakType, Break
from safeeyes.spi.state import State
from safeeyes.thread import Heartbeat, ThreadCondition, Timer, worker
from safeeyes.util.locale import _


class BreakScheduler(BreakAPI):

    def __init__(self, context: Context, heartbeat: Heartbeat, plugin_mgr: PluginManager):
        self.__context = context
        self.__heartbeat = heartbeat
        self.__condition: ThreadCondition = heartbeat.new_condition()
        self.__breaks_store = BreaksStore(context)
        self.__timer = Timer(context, heartbeat, self.__start_break)
        self.__plugins: PluginManager = plugin_mgr
        self.__skipped: bool = False
        self.__postponed: bool = False

    def start(self, next_break_time: datetime.datetime = None):
        self.__reset_stop_flags()
        self.__start(next_break_time)

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
        self.__start()

    def skip(self):
        self.__skipped = True
        self.next_break()

    def postpone(self, duration: int) -> None:
        self.__postponed = True
        next_break_time = datetime.datetime.now() + datetime.timedelta(seconds=duration)
        self.schedule(next_break_time)

    def __start(self, next_break_time: datetime.datetime = None):
        if self.__breaks_store.is_empty():
            return

        current_break = self.__breaks_store.get_break()

        if current_break is None:
            # This check is unnecessary
            return

        if next_break_time is None:
            current_time = datetime.datetime.now()
            waiting_time = current_break.waiting_time * 60
            next_break_time = current_time + datetime.timedelta(seconds=waiting_time)

        self.schedule(next_break_time)

    def schedule(self, next_break_time: datetime.datetime):
        if self.__breaks_store.is_empty():
            return
        with self.__heartbeat.lock:
            self.__context.state = State.SCHEDULING
        self.stop()

        next_break = self.__breaks_store.peek()
        if next_break is None:
            return
        short_break_time: Optional[datetime.datetime] = None
        long_break_time: Optional[datetime.datetime] = None
        if next_break.is_long_break():
            next_short_break = self.__breaks_store.peek(BreakType.SHORT)
            if next_short_break:
                short_break_time = next_break_time + datetime.timedelta(minutes=next_short_break.waiting_time)
        else:
            next_long_break = self.__breaks_store.peek(BreakType.LONG)
            if next_long_break:
                long_break_time = next_break_time + datetime.timedelta(minutes=next_long_break.waiting_time)

        self.__context.core_api.set_status(_('Next break at %s') % (utility.format_time(next_break_time)))
        self.__plugins.update_next_break(next_break, short_break_time, long_break_time)

        self.__timer.schedule(next_break_time)

    def __start_break(self):
        # BreakScheduler always call this method from a separate thread
        with self.__heartbeat.lock:
            self.__context.state = State.PRE_BREAK

        break_obj = self.__breaks_store.get_break()
        # Check if plugins want to cancel this break
        if not self.__is_break_allowed(break_obj):
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

        if self.__is_break_allowed(break_obj):
            self.__take_break(break_obj)

    def __take_break(self, break_obj: Break):
        self.__plugins.on_start_break(break_obj)
        self.__count_down(break_obj)

    def __reset_stop_flags(self) -> None:
        self.__skipped = False
        self.__postponed = False

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

        self.__plugins.on_stop_break(break_obj, self.__skipped, self.__postponed)
        self.__reset_stop_flags()
        with self.__heartbeat.lock:
            if self.__context.state != State.BREAK:
                # State changed while counting down
                return

        # Start the next break
        self.next_break()

    def __is_break_allowed(self, break_obj: Break) -> bool:
        # Check if plugins want to cancel this break
        action = self.__plugins.get_break_action(break_obj)
        if action.not_allowed():
            if action.skipped:
                # Move to the next break
                logging.info("Break '%s' is skipped by a plugin", break_obj.name)
                self.__breaks_store.next()
                self.start()
                return False
            else:
                postpone_time = action.postpone_duration
                if postpone_time <= 0:
                    break_obj.reset_time()
                    postpone_time = break_obj.waiting_time * 60
                logging.info("Break '%s' is postponed for %s seconds by a plugin", break_obj.name, postpone_time)
                next_break_time = datetime.datetime.now() + datetime.timedelta(seconds=postpone_time)
                self.schedule(next_break_time)
                return False
        return True
