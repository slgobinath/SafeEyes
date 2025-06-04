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
"""SafeEyesCore provides the core functionalities of Safe Eyes."""

import datetime
import logging
import typing

from safeeyes.model import Break
from safeeyes.model import BreakType
from safeeyes.model import BreakQueue
from safeeyes.model import EventHook
from safeeyes.model import State
from safeeyes.model import Config

from safeeyes.context import Context

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib


class SafeEyesCore:
    """Core of Safe Eyes runs the scheduler and notifies the breaks."""

    scheduled_next_break_time: typing.Optional[datetime.datetime] = None
    scheduled_next_break_timestamp: int = -1
    running: bool = False
    paused_time: float = -1
    postpone_duration: int = 0
    default_postpone_duration: int = 0
    pre_break_warning_time: int = 0
    context: Context

    _break_queue: typing.Optional[BreakQueue] = None

    # set while __wait_for is running
    _timeout_id: typing.Optional[int] = None
    _callback: typing.Optional[typing.Callable[[], None]] = None

    # set while __fire_hook is running
    _firing_hook: bool = False

    # set while taking a break
    _countdown: typing.Optional[int] = 0
    _taking_break: typing.Optional[Break] = None

    # set to true when a break was requested
    _take_break_now: bool = False

    def __init__(self, context: Context) -> None:
        """Create an instance of SafeEyesCore and initialize the variables."""
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
        self.context = context
        self.context.state = State.WAITING

    def initialize(self, config: Config):
        """Initialize the internal properties from configuration."""
        logging.info("Initialize the core")
        self.pre_break_warning_time = config.get("pre_break_warning_time")
        self._break_queue = BreakQueue.create(config, self.context)
        self.default_postpone_duration = int(config.get("postpone_duration"))
        self.postpone_unit = config.get("postpone_unit")
        if self.postpone_unit != "seconds":
            self.default_postpone_duration *= 60

        self.postpone_duration = self.default_postpone_duration

    def start(self, next_break_time=-1) -> None:
        """Start Safe Eyes is it is not running already."""
        if self._break_queue is None:
            logging.info("No breaks defined, not starting the core")
            return
        if not self.running:
            logging.info("Start Safe Eyes core")

            self.running = True
            self.scheduled_next_break_timestamp = int(next_break_time)
            self.__scheduler_job()

    def stop(self, is_resting=False) -> None:
        """Stop Safe Eyes if it is running."""
        if not self.running:
            return

        logging.info("Stop Safe Eyes core")
        self.paused_time = datetime.datetime.now().timestamp()
        # Stop the break thread
        self.running = False
        if self.context.state != State.QUIT:
            self.context.state = State.RESTING if (is_resting) else State.STOPPED

        self.__wakeup_scheduler()

    def skip(self) -> None:
        """User skipped the break using Skip button."""
        self.context.skipped = True

    def postpone(self, duration=-1) -> None:
        """User postponed the break using Postpone button."""
        if duration > 0:
            self.postpone_duration = duration
        else:
            self.postpone_duration = self.default_postpone_duration
        logging.debug("Postpone the break for %d seconds", self.postpone_duration)
        self.context.postponed = True

    def get_break_time(
        self, break_type: typing.Optional[BreakType] = None
    ) -> typing.Optional[datetime.datetime]:
        """Returns the next break time."""
        if self._break_queue is None:
            return None
        break_obj = self._break_queue.get_break_with_type(break_type)
        if not break_obj or self.scheduled_next_break_time is None:
            return None
        time = self.scheduled_next_break_time + datetime.timedelta(
            minutes=break_obj.time - self._break_queue.get_break().time
        )
        return time

    def take_break(self, break_type: typing.Optional[BreakType] = None) -> None:
        """Calling this method stops the scheduler and show the next break
        screen.
        """
        if self._break_queue is None:
            return
        if not self.context.state == State.WAITING:
            return

        if break_type is not None and self._break_queue.get_break().type != break_type:
            self._break_queue.next(break_type)

        self._take_break_now = True

        self.__wakeup_scheduler()

    def has_breaks(self, break_type: typing.Optional[BreakType] = None) -> bool:
        """Check whether Safe Eyes has breaks or not.

        Use the break_type to check for either short or long break.
        """
        if self._break_queue is None:
            return False

        if break_type is None:
            return True

        return not self._break_queue.is_empty(break_type)

    def __scheduler_job(self) -> None:
        """Scheduler task to execute during every interval."""
        if not self.running:
            return

        if self._break_queue is None:
            # This will only be called by methods which check this
            return

        current_time = datetime.datetime.now()
        current_timestamp = current_time.timestamp()

        if self.context.state == State.RESTING and self.paused_time > -1:
            # Safe Eyes was resting
            paused_duration = int(current_timestamp - self.paused_time)
            self.paused_time = -1
            next_long = self._break_queue.get_break_with_type(BreakType.LONG_BREAK)
            if next_long is not None and paused_duration > next_long.duration:
                logging.info(
                    "Skip next long break due to the pause %ds longer than break"
                    " duration",
                    paused_duration,
                )
                # Skip the next long break
                self._break_queue.skip_long_break()

        if self.context.postponed:
            # Previous break was postponed
            logging.info("Prepare for postponed break")
            time_to_wait = self.postpone_duration
            self.context.postponed = False
        elif current_timestamp < self.scheduled_next_break_timestamp:
            # Non-standard break was set.
            time_to_wait = round(
                self.scheduled_next_break_timestamp - current_timestamp
            )
            self.scheduled_next_break_timestamp = -1
        else:
            # Use next break, convert to seconds
            time_to_wait = self._break_queue.get_break().time * 60

        self.scheduled_next_break_time = current_time + datetime.timedelta(
            seconds=time_to_wait
        )
        self.context.state = State.WAITING
        self.__fire_on_update_next_break(self.scheduled_next_break_time)

        # Wait for the pre break warning period
        if self.postpone_unit == "seconds":
            logging.info("Waiting for %d seconds until next break", time_to_wait)
        else:
            logging.info("Waiting for %d minutes until next break", (time_to_wait / 60))

        self.__wait_for(time_to_wait, self.__do_pre_break)

    def __fire_on_update_next_break(self, next_break_time: datetime.datetime) -> None:
        """Pass the next break information to the registered listeners."""
        if self._break_queue is None:
            # This will only be called by methods which check this
            return
        self.__fire_hook(
            self.on_update_next_break, self._break_queue.get_break(), next_break_time
        )

    def __do_pre_break(self) -> None:
        if self._take_break_now:
            self._take_break_now = False
            logging.info("Take a break due to external request")
            self.__do_start_break()
            return

        logging.info("Pre-break waiting is over")

        if not self.running:
            # This can be reached if another thread changed running while __wait_for was
            # blocking
            return

        self.__fire_pre_break()

    def __fire_pre_break(self) -> None:
        """Show the notification and start the break after the notification."""
        if self._break_queue is None:
            # This will only be called by methods which check this
            return
        self.context.state = State.PRE_BREAK
        proceed = self.__fire_hook(self.on_pre_break, self._break_queue.get_break())
        if not proceed:
            # Plugins wanted to ignore this break
            self.__start_next_break()
            return

        self.__wait_until_prepare()

    def __wait_until_prepare(self) -> None:
        logging.info(
            "Wait for %d seconds before the break", self.pre_break_warning_time
        )
        # Wait for the pre break warning period
        self.__wait_for(self.pre_break_warning_time, self.__do_start_break)

    def __postpone_break(self) -> None:
        self.__wait_for(self.postpone_duration, self.__do_start_break)

    def __do_start_break(self) -> None:
        if self._take_break_now:
            # already taking a break now, ignore
            self._take_break_now = False

        if not self.running:
            return
        if self._break_queue is None:
            # This will only be called by methods which check this
            return
        break_obj = self._break_queue.get_break()
        # Show the break screen
        proceed = self.__fire_hook(self.on_start_break, break_obj)
        if not proceed:
            # Plugins want to ignore this break
            self.__start_next_break()
            return
        if self.context.postponed:
            # Plugins want to postpone this break
            self.context.postponed = False

            if self.scheduled_next_break_time is None:
                raise Exception("this should never happen")

            # Update the next break time
            self.scheduled_next_break_time = (
                self.scheduled_next_break_time
                + datetime.timedelta(seconds=self.postpone_duration)
            )
            self.__fire_on_update_next_break(self.scheduled_next_break_time)
            # Wait in user thread
            self.__postpone_break()
        else:
            self.__fire_hook(self.start_break, break_obj)
            self.__start_break()

    def __start_break(self) -> None:
        """Start the break screen."""
        if self._break_queue is None:
            # This will only be called by methods which check this
            return
        self.context.state = State.BREAK
        break_obj = self._break_queue.get_break()
        self._taking_break = break_obj
        self._countdown = break_obj.duration

        self.__cycle_break_countdown()

    def __cycle_break_countdown(self) -> None:
        if self._taking_break is None or self._countdown is None:
            raise Exception("countdown running without countdown or break")

        if self._take_break_now:
            logging.warning("Break requested while already taking a break")
            self._take_break_now = False

        if (
            self._countdown > 0
            and self.running
            and not self.context.skipped
            and not self.context.postponed
        ):
            countdown = self._countdown
            self._countdown -= 1

            total_break_time = self._taking_break.duration
            seconds = total_break_time - countdown
            self.__fire_hook(self.on_count_down, countdown, seconds)
            # Sleep for 1 second
            self.__wait_for(1, self.__cycle_break_countdown)
        else:
            self._countdown = None
            self._taking_break = None

            self.__fire_stop_break()

    def __fire_stop_break(self) -> None:
        # Loop terminated because of timeout (not skipped) -> Close the break alert
        if not self.context.skipped and not self.context.postponed:
            logging.info("Break is terminated automatically")
            self.__fire_hook(self.on_stop_break)

        # Reset the skipped flag
        self.context.skipped = False
        self.context.skip_button_disabled = False
        self.context.postpone_button_disabled = False
        self.__start_next_break()

    def __wait_for(
        self,
        duration: int,
        callback: typing.Callable[[], None],
    ) -> None:
        """Wait until someone wake up or the timeout happens."""
        if self._callback is not None or self._timeout_id is not None:
            raise Exception("this should not be called reentrantly")

        self._callback = callback
        self._timeout_id = GLib.timeout_add_seconds(duration, self.__on_wakeup)

    def __on_wakeup(self) -> bool:
        if self._callback is None or self._timeout_id is None:
            raise Exception("Woken up but no callback")

        callback = self._callback

        self._timeout_id = None
        self._callback = None

        callback()

        # This signals that the callback should only be called once
        return GLib.SOURCE_REMOVE

    def __fire_hook(
        self,
        hook: EventHook,
        *args,
        **kwargs,
    ) -> bool:
        if self._firing_hook:
            raise Exception("this should not be called reentrantly")

        self._firing_hook = True

        proceed = hook.fire(*args, **kwargs)

        self._firing_hook = False

        return proceed

    def __wakeup_scheduler(self) -> None:
        if (self._callback is None) != (self._timeout_id is None):
            # either both are set or none are set
            raise Exception("This should never happen")

        if (self._callback is None) and not self._firing_hook:
            # neither is set - not running
            raise Exception("trying to queue action while core is not running")
        elif (self._callback is not None) and self._firing_hook:
            # both are set
            raise Exception("This should never happen")

        if self._callback is not None and self._timeout_id is not None:
            callback = self._callback

            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
            self._callback = None

            callback()
        elif self._firing_hook:
            # plugin is running
            pass

    def __start_next_break(self) -> None:
        if self._break_queue is None:
            # This will only be called by methods which check this
            return
        if not self.context.postponed:
            self._break_queue.next()

        if self.running:
            # Schedule the break again
            self.__wait_for(0, self.__scheduler_job)
