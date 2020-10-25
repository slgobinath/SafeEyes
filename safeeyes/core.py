#!/usr/bin/env python
# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2016  Gobinath

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
SafeEyesCore provides the core functionalities of Safe Eyes.
"""

import datetime
import logging
import threading
import time

from safeeyes import utility
from safeeyes.model import Break
from safeeyes.model import BreakType
from safeeyes.model import BreakQueue
from safeeyes.model import EventHook
from safeeyes.model import State


class SafeEyesCore:
    """
    Core of Safe Eyes runs the scheduler and notifies the breaks.
    """

    def __init__(self, context):
        """
        Create an instance of SafeEyesCore and initialize the variables.
        """
        self.break_queue = None
        self.postpone_duration = 0
        self.default_postpone_duration = 0
        self.pre_break_warning_time = 0
        self.running = False
        self.scheduled_next_break_timestamp = -1
        self.scheduled_next_break_time = None
        self.paused_time = -1
        # This event is fired before <time-to-prepare> for a break
        self.on_pre_break = EventHook()
        # This event is fired just before the start of a break
        self.on_start_break = EventHook()
        # This event is fired at the start of a break
        self.start_break = EventHook()
        # This event is fired during every count down
        self.on_count_down = EventHook()
        # This event is fired at the end of a break
        self.on_stop_break = EventHook()
        # This event is fired when deciding the next break time
        self.on_update_next_break = EventHook()
        self.waiting_condition = threading.Condition()
        self.lock = threading.Lock()
        self.context = context
        self.context['skipped'] = False
        self.context['postponed'] = False
        self.context['state'] = State.WAITING

    def initialize(self, config):
        """
        Initialize the internal properties from configuration
        """
        logging.info("Initialize the core")
        self.pre_break_warning_time = config.get('pre_break_warning_time')
        self.break_queue = BreakQueue(config, self.context)
        self.default_postpone_duration = config.get('postpone_duration') * 60   # Convert to seconds
        self.postpone_duration = self.default_postpone_duration

    def start(self, next_break_time=-1, reset_breaks=False):
        """
        Start Safe Eyes is it is not running already.
        """
        if self.break_queue.is_empty():
            return
        with self.lock:
            if not self.running:
                logging.info("Start Safe Eyes core")
                if reset_breaks:
                    logging.info("Reset breaks to start from the beginning")
                    self.break_queue.reset()

                self.running = True
                self.scheduled_next_break_timestamp = int(next_break_time)
                utility.start_thread(self.__scheduler_job)

    def stop(self):
        """
        Stop Safe Eyes if it is running.
        """
        with self.lock:
            if not self.running:
                return

            logging.info("Stop Safe Eyes core")
            self.paused_time = datetime.datetime.now().timestamp()
            # Stop the break thread
            self.waiting_condition.acquire()
            self.running = False
            if self.context['state'] != State.QUIT:
                self.context['state'] = State.STOPPED
            self.waiting_condition.notify_all()
            self.waiting_condition.release()

    def skip(self):
        """
        User skipped the break using Skip button
        """
        self.context['skipped'] = True

    def postpone(self, duration=-1):
        """
        User postponed the break using Postpone button
        """
        if duration > 0:
            self.postpone_duration = duration
        else:
            self.postpone_duration = self.default_postpone_duration
        logging.debug("Postpone the break for %d seconds", self.postpone_duration)
        self.context['postponed'] = True

    def take_break(self):
        """
        Calling this method stops the scheduler and show the next break screen
        """
        if self.break_queue.is_empty():
            return
        if not self.context['state'] == State.WAITING:
            return
        utility.start_thread(self.__take_break)

    def has_breaks(self):
        """
        Check whether Safe Eyes has breaks or not.
        """
        return not self.break_queue.is_empty()

    def __take_break(self):
        """
        Show the next break screen
        """
        logging.info('Take a break due to external request')

        with self.lock:
            if not self.running:
                return

            logging.info("Stop the scheduler")

            # Stop the break thread
            self.waiting_condition.acquire()
            self.running = False
            self.waiting_condition.notify_all()
            self.waiting_condition.release()
            time.sleep(1)  # Wait for 1 sec to ensure the sceduler is dead
            self.running = True

        utility.execute_main_thread(self.__fire_start_break)

    def __scheduler_job(self):
        """
        Scheduler task to execute during every interval
        """
        if not self.running:
            return

        self.context['state'] = State.WAITING
        # Convert to seconds
        time_to_wait = self.break_queue.get_break().time * 60
        current_time = datetime.datetime.now()
        current_timestamp = current_time.timestamp()

        if self.context['postponed']:
            # Previous break was postponed
            logging.info('Prepare for postponed break')
            time_to_wait = self.postpone_duration
            self.context['postponed'] = False

        elif self.paused_time > -1 and self.break_queue.is_long_break():
            # Safe Eyes was paused earlier and next break is long
            paused_duration = int(current_timestamp - self.paused_time)
            self.paused_time = -1
            if paused_duration > self.break_queue.get_break().duration:
                logging.info('Skip next long break due to the pause longer than break duration')
                # Skip the next long break
                self.break_queue.next()

        if current_timestamp < self.scheduled_next_break_timestamp:
            time_to_wait = round(self.scheduled_next_break_timestamp - current_timestamp)
            self.scheduled_next_break_timestamp = -1

        self.scheduled_next_break_time = current_time + datetime.timedelta(seconds=time_to_wait)
        utility.execute_main_thread(self.__fire_on_update_next_break, self.scheduled_next_break_time)

        # Wait for the pre break warning period
        logging.info("Waiting for %d minutes until next break", (time_to_wait / 60))
        self.__wait_for(time_to_wait)

        logging.info("Pre-break waiting is over")

        if not self.running:
            return
        utility.execute_main_thread(self.__fire_pre_break)

    def __fire_on_update_next_break(self, next_break_time):
        """
        Pass the next break information to the registered listeners.
        """
        self.on_update_next_break.fire(self.break_queue.get_break(), next_break_time)

    def __fire_pre_break(self):
        """
        Show the notification and start the break after the notification.
        """
        self.context['state'] = State.PRE_BREAK
        if not self.on_pre_break.fire(self.break_queue.get_break()):
            # Plugins wanted to ignore this break
            self.__start_next_break()
            return
        utility.start_thread(self.__wait_until_prepare)

    def __wait_until_prepare(self):
        logging.info("Wait for %d seconds before the break", self.pre_break_warning_time)
        # Wait for the pre break warning period
        self.__wait_for(self.pre_break_warning_time)
        if not self.running:
            return
        utility.execute_main_thread(self.__fire_start_break)

    def __postpone_break(self):
        self.__wait_for(self.postpone_duration)
        utility.execute_main_thread(self.__fire_start_break)

    def __fire_start_break(self):
        # Show the break screen
        if not self.on_start_break.fire(self.break_queue.get_break()):
            # Plugins want to ignore this break
            self.__start_next_break()
            return
        if self.context['postponed']:
            # Plugins want to postpone this break
            self.context['postponed'] = False
            # Update the next break time
            self.scheduled_next_break_time = self.scheduled_next_break_time + datetime.timedelta(seconds=self.postpone_duration)
            self.__fire_on_update_next_break(self.scheduled_next_break_time)
            # Wait in user thread
            utility.start_thread(self.__postpone_break)
        else:
            self.start_break.fire(self.break_queue.get_break())
            utility.start_thread(self.__start_break)

    def __start_break(self):
        """
        Start the break screen.
        """
        self.context['state'] = State.BREAK
        break_obj = self.break_queue.get_break()
        countdown = break_obj.duration
        total_break_time = countdown

        while countdown and self.running and not self.context['skipped'] and not self.context['postponed']:
            seconds = total_break_time - countdown
            self.on_count_down.fire(countdown, seconds)
            time.sleep(1)    # Sleep for 1 second
            countdown -= 1
        utility.execute_main_thread(self.__fire_stop_break)

    def __fire_stop_break(self):
        # Loop terminated because of timeout (not skipped) -> Close the break alert
        if not self.context['skipped'] and not self.context['postponed']:
            logging.info("Break is terminated automatically")
            self.on_stop_break.fire()

        # Reset the skipped flag
        self.context['skipped'] = False
        self.__start_next_break()

    def __wait_for(self, duration):
        """
        Wait until someone wake up or the timeout happens.
        """
        self.waiting_condition.acquire()
        self.waiting_condition.wait(duration)
        self.waiting_condition.release()

    def __start_next_break(self):
        if not self.context['postponed']:
            self.break_queue.next()

        if self.running:
            # Schedule the break again
            utility.start_thread(self.__scheduler_job)
