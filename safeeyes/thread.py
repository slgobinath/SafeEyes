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
import datetime
import logging
import threading
import time
from typing import List, Optional, Callable

from safeeyes.context import Context
from safeeyes.spi.api import ThreadAPI, Condition
from safeeyes.spi.state import State


def main(fun):
    def run(*k, **kw):
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import GLib
        GLib.idle_add(lambda: fun(*k, **kw))

    return run


def worker(fun):
    def run(*k, **kw):
        t = threading.Thread(target=fun, args=k, kwargs=kw, daemon=False, name="WorkThread")
        t.start()

    return run


class ThreadCondition(Condition):

    def __init__(self):
        self.__waiting_condition: threading.Condition = threading.Condition()

    def hold(self, timeout: int):
        self.__waiting_condition.acquire()
        self.__waiting_condition.wait(timeout)
        self.__waiting_condition.release()

    def release_all(self):
        """
        Release all waiting threads so that they will continue executing their remaining tasks.
        """
        self.__waiting_condition.acquire()
        self.__waiting_condition.notify_all()
        self.__waiting_condition.release()


class Heartbeat(ThreadAPI):
    def __init__(self, context: Context):
        self.__waiting_condition: threading.Condition = threading.Condition()
        self.__context: Context = context
        self.running: bool = False
        self.lock = threading.Lock()
        self.__conditions: List[ThreadCondition] = []

    def start(self) -> None:
        """
        Stop the heartbeat.
        """
        self.running = True

    def stop(self) -> None:
        """
        Stop the heartbeat.
        """
        self.__waiting_condition.acquire()
        self.running = False
        if self.__context.state != State.QUIT:
            self.__context.state = State.STOPPED
        self.__waiting_condition.notify_all()
        self.__waiting_condition.release()

    def release_all(self) -> None:
        """
        Release all waiting threads so that they will continue executing their remaining tasks.
        """
        for condition in self.__conditions:
            condition.release_all()

        self.__waiting_condition.acquire()
        self.__waiting_condition.notify_all()
        self.__waiting_condition.release()

    def restart(self) -> None:
        self.__waiting_condition.acquire()
        self.running = False
        self.__waiting_condition.notify_all()
        self.__waiting_condition.release()
        time.sleep(1)  # Wait for 1 sec to ensure the scheduler is dead
        self.running = True

    def hold(self, timeout: int) -> None:
        self.__waiting_condition.acquire()
        self.__waiting_condition.wait(timeout)
        self.__waiting_condition.release()

    def new_condition(self) -> ThreadCondition:
        condition = ThreadCondition()
        self.__conditions.append(condition)
        return condition


class Timer:

    def __init__(self, context: Context, heartbeat: Heartbeat, on_timeout: Callable[[], None]):
        self.__context = context
        import datetime
        self.__next_schedule: Optional[datetime.datetime] = None
        self.__heartbeat: Heartbeat = heartbeat
        self.__on_timeout: Callable[[], None] = on_timeout
        self.__condition: ThreadCondition = heartbeat.new_condition()
        self.__running = False

    def schedule(self, next_break_at: datetime.datetime):
        self.__next_schedule = next_break_at

        with self.__heartbeat.lock:
            if not self.__running:
                self.__running = True
                self.__schedule()
            else:
                # Scheduler is already running
                # Release all threads to notify that something has changed
                self.__condition.release_all()

    def stop(self):
        with self.__heartbeat.lock:
            self.__running = False
            self.__condition.release_all()

    @worker
    def __schedule(self) -> None:
        self.__context.state = State.WAITING
        time_to_wait = self.__get_waiting_time()
        while self.__heartbeat.running and self.__running and time_to_wait > 0:
            # Wait for the pre break warning period
            logging.debug("Timer waiting for %d minutes", (time_to_wait / 60))
            self.__condition.hold(time_to_wait)
            time_to_wait = self.__get_waiting_time()

        if self.__heartbeat.running and self.__running and self.__context.state == State.WAITING:
            self.__on_timeout()

    def __get_waiting_time(self) -> int:
        if self.__next_schedule is None:
            # No pre-defined waiting time
            return 0
        current_time = datetime.datetime.now()
        remaining_time = 0
        if current_time < self.__next_schedule:
            remaining_time = (self.__next_schedule - current_time).seconds

        return remaining_time
