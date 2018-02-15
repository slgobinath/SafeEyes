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
import subprocess
import threading

from safeeyes import Utility
from safeeyes.model import State

"""
Safe Eyes smart pause plugin
"""

context = None
idle_condition = threading.Condition()
lock = threading.Lock()
active = False
idle_time = 0
enable_safe_eyes = None
disable_safe_eyes = None
smart_pause_activated = False
idle_start_time = None
next_break_time = None
next_break_duration = 0
break_interval = 0
waiting_time = 2
interpret_idle_as_break = False


def __system_idle_time():
    """
    Get system idle time in minutes.
    Return the idle time if xprintidle is available, otherwise return 0.
    """
    try:
        return int(subprocess.check_output(['xprintidle']).decode('utf-8')) / 1000    # Convert to seconds
    except BaseException:
        return 0


def __is_active():
    """
    Thread safe function to see if this plugin is active or not.
    """
    is_active = False
    with lock:
        is_active = active
    return is_active


def __set_active(is_active):
    """
    Thread safe function to change the state of the plugin.
    """
    global active
    with lock:
        active = is_active


def init(ctx, safeeyes_config, plugin_config):
    """
    Initialize the plugin.
    """
    global context
    global enable_safe_eyes
    global disable_safe_eyes
    global idle_time
    global break_interval
    global waiting_time
    global interpret_idle_as_break
    logging.debug('Initialize Smart Pause plugin')
    context = ctx
    enable_safe_eyes = context['api']['enable_safeeyes']
    disable_safe_eyes = context['api']['disable_safeeyes']
    idle_time = plugin_config['idle_time']
    interpret_idle_as_break = plugin_config['interpret_idle_as_break']
    break_interval = safeeyes_config.get('break_interval') * 60  # Convert to seconds
    waiting_time = min(2, idle_time)    # If idle time is 1 sec, wait only 1 sec


def __start_idle_monitor():
    """
    Continuously check the system idle time and pause/resume Safe Eyes based on it.
    """
    global smart_pause_activated
    global idle_start_time
    while __is_active():
        # Wait for waiting_time seconds
        idle_condition.acquire()
        idle_condition.wait(waiting_time)
        idle_condition.release()

        if __is_active():
            # Get the system idle time
            system_idle_time = __system_idle_time()
            if system_idle_time >= idle_time and context['state'] == State.WAITING:
                smart_pause_activated = True
                idle_start_time = datetime.datetime.now()
                logging.info('Pause Safe Eyes due to system idle')
                disable_safe_eyes(None)
            elif system_idle_time < idle_time and context['state'] == State.STOPPED:
                logging.info('Resume Safe Eyes due to user activity')
                smart_pause_activated = False
                idle_period = (datetime.datetime.now() - idle_start_time)
                idle_seconds = idle_period.total_seconds()
                if interpret_idle_as_break and idle_seconds >= next_break_duration:
                    # User is idle for break duration and wants to consider it as a break
                    enable_safe_eyes()
                elif idle_seconds < break_interval:
                    # Credit back the idle time
                    next_break = next_break_time + idle_period
                    enable_safe_eyes(next_break.timestamp())
                else:
                    # User is idle for more than the time between two breaks
                    enable_safe_eyes()


def on_start():
    """
    Start a thread to continuously call xprintidle.
    """
    global active
    if not __is_active():
        # If SmartPause is already started, do not start it again
        logging.debug('Start Smart Pause plugin')
        __set_active(True)
        Utility.start_thread(__start_idle_monitor)


def on_stop():
    """
    Stop the thread from continuously calling xprintidle.
    """
    global active
    global smart_pause_activated
    if smart_pause_activated:
        # Safe Eyes is stopped due to system idle
        smart_pause_activated = False
        return
    logging.debug('Stop Smart Pause plugin')
    __set_active(False)
    idle_condition.acquire()
    idle_condition.notify_all()
    idle_condition.release()


def update_next_break(break_obj, dateTime):
    """
    Update the next break time.
    """
    global next_break_time
    global next_break_duration
    next_break_time = dateTime
    next_break_duration = break_obj.time
