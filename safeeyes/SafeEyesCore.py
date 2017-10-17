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

from safeeyes import Utility
from safeeyes.model import Break
from safeeyes.model import BreakType
from safeeyes.model import EventHook
from safeeyes.model import State


class SafeEyesCore(object):
    """
    Core of Safe Eyes runs the scheduler and notifies the breaks.
    """

    def __init__(self, context):
        """
        Create an instance of SafeEyesCore and initialize the variables.
        """
        self.break_count = 0
        self.break_interval = 0
        self.breaks = None
        self.long_break_duration = 0
        self.next_break_index = context['session'].get('next_break_index', 0)
        self.postpone_duration = 0
        self.pre_break_warning_time = 0
        self.running = False
        self.short_break_duration = 0
        self.scheduled_next_break_time = -1
        # This event is fired before <time-to-prepare> for a break
        self.on_pre_break = EventHook()
        # This event is fired at the start of a break
        self.on_start_break = EventHook()
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
        self.context['new_cycle'] = False

    def initialize(self, config):
        """
        Initialize the internal properties from configuration
        """
        logging.info("Initialize the core")
        self.breaks = []
        self.pre_break_warning_time = config.get('pre_break_warning_time')
        self.long_break_duration = config.get('long_break_duration')
        self.short_break_duration = config.get('short_break_duration')
        self.break_interval = config.get('break_interval') * 60   # Convert to seconds
        self.postpone_duration = config.get('postpone_duration') * 60   # Convert to seconds

        self.__init_breaks(BreakType.SHORT_BREAK, config.get('short_breaks'), config.get('no_of_short_breaks_per_long_break'))
        self.__init_breaks(BreakType.LONG_BREAK, config.get('long_breaks'), config.get('no_of_short_breaks_per_long_break'))
        self.break_count = len(self.breaks)
        if self.break_count == 0:
            # No breaks found
            return
        self.next_break_index = (self.next_break_index) % self.break_count
        self.context['session']['next_break_index'] = self.next_break_index

    def start(self, next_break_time=-1):
        """
        Start Safe Eyes is it is not running already.
        """
        if not self.has_breaks():
            return
        with self.lock:
            if not self.running:
                logging.info("Start Safe Eyes core")
                self.running = True
                self.scheduled_next_break_time = int(next_break_time)
                Utility.start_thread(self.__scheduler_job)

    def stop(self):
        """
        Stop Safe Eyes if it is running.
        """
        with self.lock:
            if not self.running:
                return

            logging.info("Stop Safe Eye core")

            # Prevent resuming from a long break
            if self.has_breaks() and self.__is_long_break():
                # Next break will be a long break.
                self.__select_next_break()

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

    def postpone(self):
        """
        User postponed the break using Postpone button
        """
        self.context['postponed'] = True

    def take_break(self):
        """
        Calling this method stops the scheduler and show the next break screen
        """
        if not self.has_breaks():
            return
        if not self.context['state'] == State.WAITING:
            return
        Utility.start_thread(self.__take_break)

    def has_breaks(self):
        """
        Check whether Safe Eyes has breaks or not.
        """
        return bool(self.breaks)

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

        self.context['new_cycle'] = self.next_break_index == 0
        Utility.execute_main_thread(self.__fire_start_break)

    def __scheduler_job(self):
        """
        Scheduler task to execute during every interval
        """
        if not self.running:
            return

        self.context['state'] = State.WAITING
        time_to_wait = self.break_interval

        if self.context['postponed']:
            # Wait until the postpone time
            time_to_wait = self.postpone_duration
            self.context['postponed'] = False

        current_time = datetime.datetime.now()
        current_timestamp = current_time.timestamp()
        if current_timestamp < self.scheduled_next_break_time:
            time_to_wait = round(self.scheduled_next_break_time - current_timestamp)
            self.scheduled_next_break_time = -1

        next_break_time = current_time + datetime.timedelta(seconds=time_to_wait)
        Utility.execute_main_thread(self.__fire_on_update_next_break, next_break_time)

        if self.__is_long_break():
            self.context['break_type'] = 'long'
        else:
            self.context['break_type'] = 'short'

        # Wait for the pre break warning period
        logging.info("Waiting for %d minutes until next break", (time_to_wait / 60))
        self.__wait_for(time_to_wait)

        logging.info("Pre-break waiting is over")

        if not self.running:
            return

        self.context['new_cycle'] = self.next_break_index == 0
        Utility.execute_main_thread(self.__fire_pre_break)

    def __fire_on_update_next_break(self, next_break_time):
        """
        Pass the next break information to the registered listeners.
        """
        self.on_update_next_break.fire(self.breaks[self.next_break_index], next_break_time)

    def __fire_pre_break(self):
        """
        Show the notification and start the break after the notification.
        """
        self.context['state'] = State.PRE_BREAK
        if not self.on_pre_break.fire(self.breaks[self.next_break_index]):
            # Plugins wanted to ignore this break
            self.__start_next_break()
            return
        Utility.start_thread(self.__wait_until_prepare)

    def __wait_until_prepare(self):
        logging.info("Wait for %d seconds before the break", self.pre_break_warning_time)
        # Wait for the pre break warning period
        self.__wait_for(self.pre_break_warning_time)
        if not self.running:
            return
        Utility.execute_main_thread(self.__fire_start_break)

    def __fire_start_break(self):
        # Show the break screen
        if not self.on_start_break.fire(self.breaks[self.next_break_index]):
            # Plugins wanted to ignore this break
            self.__start_next_break()
            return
        Utility.start_thread(self.__start_break)

    def __start_break(self):
        """
        Start the break screen.
        """
        self.context['state'] = State.BREAK
        break_obj = self.breaks[self.next_break_index]
        countdown = break_obj.time
        total_break_time = countdown

        while countdown and self.running and not self.context['skipped'] and not self.context['postponed']:
            seconds = total_break_time - countdown
            self.on_count_down.fire(countdown, seconds)
            time.sleep(1)    # Sleep for 1 second
            countdown -= 1
        Utility.execute_main_thread(self.__fire_stop_break)

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

    def __select_next_break(self):
        """
        Select the next break.
        """
        self.next_break_index = (self.next_break_index + 1) % self.break_count
        self.context['session']['next_break_index'] = self.next_break_index

    def __is_long_break(self):
        """
        Check if the next break is long break.
        """
        return self.breaks[self.next_break_index].type is BreakType.LONG_BREAK

    def __start_next_break(self):
        if not self.context['postponed']:
            self.__select_next_break()

        if self.running:
            # Schedule the break again
            Utility.start_thread(self.__scheduler_job)

    def __init_breaks(self, break_type, break_configs, short_breaks_per_long_break=0):
        """
        Fill the self.breaks using short and local breaks.
        """
        # Defin the default break time
        default_break_time = self.short_break_duration

        # Duplicate short breaks to equally distribute the long breaks
        if break_type is BreakType.LONG_BREAK:
            if self.breaks:
                default_break_time = self.long_break_duration
                required_short_breaks = short_breaks_per_long_break * len(break_configs)
                no_of_short_breaks = len(self.breaks)
                short_break_index = 0
                while no_of_short_breaks < required_short_breaks:
                    self.breaks.append(self.breaks[short_break_index])
                    short_break_index += 1
                    no_of_short_breaks += 1
            else:
                # If there are no short breaks, extend the break interval according to long break interval
                self.break_interval = int(self.break_interval * short_breaks_per_long_break)

        iteration = 1
        for break_config in break_configs:
            name = _(break_config['name'])
            break_time = break_config.get('duration', default_break_time)
            image = break_config.get('image')
            plugins = break_config.get('plugins', None)

            # Validate time value
            if not isinstance(break_time, int) or break_time <= 0:
                logging.error('Invalid time in break: ' + str(break_config))
                continue

            break_obj = Break(break_type, name, break_time, image, plugins)
            if break_type is BreakType.SHORT_BREAK:
                self.breaks.append(break_obj)
            else:
                # Long break
                index = iteration * (short_breaks_per_long_break + 1) - 1
                self.breaks.insert(index, break_obj)
                iteration += 1
