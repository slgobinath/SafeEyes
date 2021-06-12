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

import datetime
import logging
import re
import subprocess
import threading
from typing import Optional

from safeeyes.context import Context
from safeeyes.spi.breaks import Break
from safeeyes.spi.plugin import BreakAction
from safeeyes.spi.state import State
from safeeyes.thread import ThreadCondition, worker


class SmartPause:

    def __init__(self, context: Context, config: dict):
        self.__context = context
        self.__lock: threading.Lock = threading.Lock()
        self.__condition: ThreadCondition = context.thread_api.new_condition()
        self.__postpone_if_active = config['postpone_if_active']
        self.__idle_time = config['idle_time']
        self.__interpret_idle_as_break = config['interpret_idle_as_break']
        self.__short_break_interval = context.config.get('short_break_interval') * 60  # Convert to seconds
        self.__long_break_duration = context.config.get('long_break_duration')
        self.__waiting_time = min(2, self.__idle_time)  # If idle time is 1 sec, wait only 1 sec
        self.__is_wayland_and_gnome = context.env.name == 'gnome' and context.env.is_wayland()
        self.__active: bool = False
        self.__smart_pause_activated: bool = False
        self.__next_break_time: datetime.datetime = None
        self.__next_break_duration: int = 0
        self.__idle_start_time: Optional[datetime.datetime] = None

    def start(self) -> None:
        if not self.__is_active():
            # If SmartPause is already started, do not start it again
            logging.debug('Start Smart Pause plugin')
            self.__set_active(True)
            self.__start_idle_monitor()

    def stop(self) -> None:
        if self.__smart_pause_activated:
            # Safe Eyes is stopped due to system idle
            self.__smart_pause_activated = False
            return
        logging.debug('Stop Smart Pause plugin')
        self.__set_active(False)
        self.__condition.release_all()

    def set_next_break(self, break_obj: Break, date_time: datetime.datetime) -> None:
        """
        Update the next break time.
        """
        self.__next_break_time = date_time
        self.__next_break_duration = break_obj.duration

    def should_postpone(self) -> bool:
        if self.__postpone_if_active:
            # Postpone this break if the user is active
            system_idle_time = self.__system_idle_time()
            return system_idle_time < 2
        return False

    def clean(self) -> None:
        session_config = self.__context.session.get_plugin('smartpause')
        session_config.pop('idle_period', None)

    def __system_idle_time(self) -> int:
        if self.__is_wayland_and_gnome:
            return SmartPause.__gnome_wayland_idle_time()
        else:
            return SmartPause.__xorg_idle_time()

    def __is_active(self):
        """
        Thread safe function to see if this plugin is active or not.
        """
        is_active = False
        with self.__lock:
            is_active = self.__active
        return is_active

    def __set_active(self, is_active):
        """
        Thread safe function to change the state of the plugin.
        """
        with self.__lock:
            self.__active = is_active

    @worker
    def __start_idle_monitor(self):
        """
        Continuously check the system idle time and pause/resume Safe Eyes based on it.
        """
        while self.__is_active():
            # Wait for waiting_time seconds
            self.__condition.hold(self.__waiting_time)
            if self.__is_active():
                # Get the system idle time
                system_idle_time = self.__system_idle_time()
                if system_idle_time >= self.__idle_time and self.__context.state == State.WAITING:
                    self.__smart_pause_activated = True
                    self.__idle_start_time = datetime.datetime.now() - datetime.timedelta(seconds=system_idle_time)
                    logging.info('Pause Safe Eyes due to system idle')
                    self.__context.core_api.stop()

                elif system_idle_time < self.__idle_time and self.__context.state == State.STOPPED and self.__idle_start_time is not None:
                    logging.info('Resume Safe Eyes due to user activity')
                    self.__smart_pause_activated = False
                    idle_period = (datetime.datetime.now() - self.__idle_start_time)
                    idle_seconds = idle_period.total_seconds()

                    session_config = self.__context.session.get_plugin('smartpause')
                    session_config['idle_period'] = idle_seconds
                    self.__context.session.set_plugin('smartpause', session_config)

                    if self.__interpret_idle_as_break and idle_seconds >= self.__next_break_duration:
                        # User is idle for break duration and wants to consider it as a break
                        logging.debug("Idle for %d seconds, long break %d", idle_seconds, self.__long_break_duration)
                        self.__context.core_api.start(
                            reset_breaks=(idle_seconds >= self.__long_break_duration))
                    elif idle_seconds < self.__short_break_interval:
                        # Credit back the idle time
                        if self.__next_break_time is not None:
                            # This method runs in a thread since the start.
                            # It may run before next_break is initialized in the update_next_break method
                            next_break = self.__next_break_time + idle_period
                            self.__context.core_api.start(next_break)
                        else:
                            self.__context.core_api.start()
                    else:
                        # User is idle for more than the time between two breaks
                        self.__context.core_api.start()

    @staticmethod
    def __xorg_idle_time():
        """
        Get system idle time in minutes.
        Return the idle time if xprintidle is available, otherwise return 0.
        """
        try:
            # Convert to seconds
            return int(subprocess.check_output(['xprintidle']).decode('utf-8')) / 1000
        except BaseException as e:
            logging.warning("Failed to get system idle time for xorg.")
            logging.warning(str(e))
            return 0

    @staticmethod
    def __gnome_wayland_idle_time():
        """
        Determine system idle time in seconds, specifically for gnome with wayland.
        If there's a failure, return 0.
        https://unix.stackexchange.com/a/492328/222290
        """
        try:
            output = subprocess.check_output([
                'dbus-send',
                '--print-reply',
                '--dest=org.gnome.Mutter.IdleMonitor',
                '/org/gnome/Mutter/IdleMonitor/Core',
                'org.gnome.Mutter.IdleMonitor.GetIdletime'
            ])
            return int(re.search(rb'\d+$', output).group(0)) / 1000
        except BaseException as e:
            logging.warning("Failed to get system idle time for gnome/wayland.")
            logging.warning(str(e))
            return 0


smart_pause: SmartPause


def init(context: Context, plugin_config: dict):
    """
    Initialize the plugin.
    """
    logging.info('Initialize Smart Pause plugin')
    global smart_pause
    smart_pause = SmartPause(context, plugin_config)


def on_start() -> None:
    """
    Start a thread to continuously call xprintidle.
    """
    smart_pause.start()


def on_stop():
    """
    Stop the thread from continuously calling xprintidle.
    """
    smart_pause.stop()


def update_next_break(break_obj: Break, next_short_break_time: Optional[datetime.datetime],
                      next_long_break_time: Optional[datetime.datetime]) -> None:
    """
    Update the next break time.
    """
    next_break_time: Optional[datetime.datetime] = None
    if next_short_break_time is not None:
        next_break_time = next_short_break_time if next_long_break_time is None or next_short_break_time < next_long_break_time else next_long_break_time
    elif next_long_break_time is not None:
        next_break_time = next_long_break_time if next_short_break_time is None or next_long_break_time < next_short_break_time else next_short_break_time
    if next_break_time:
        smart_pause.set_next_break(break_obj, next_break_time)


def get_break_action(break_obj: Break) -> Optional[BreakAction]:
    """
    Called just before on_pre_break and on_start_break.
    This is the opportunity for plugins to skip/postpone a break.
    None means BreakAction.allow()
    """
    if smart_pause.should_postpone():
        return BreakAction.postpone(2)
    return BreakAction.allow()


def disable():
    """
    SmartPause plugin was active earlier but now user has disabled it.
    """
    # Remove the idle_period
    smart_pause.clean()
