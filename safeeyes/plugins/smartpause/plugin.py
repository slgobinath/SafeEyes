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
import re

from safeeyes import utility
from safeeyes.model import State

"""
Safe Eyes smart pause plugin
"""

context = None
idle_condition = threading.Condition()
lock = threading.Lock()
active = False
idle_time = 0
enable_safeeyes = None
disable_safeeyes = None
smart_pause_activated = False
idle_start_time = None
next_break_time = None
next_break_duration = 0
short_break_interval = 0
waiting_time = 2
is_wayland_and_gnome = False

use_swayidle = False
use_ext_idle_notify = False
swayidle_process = None
swayidle_lock = threading.Lock()
swayidle_idle = 0
swayidle_active = 0

ext_idle_notify_lock = threading.Lock()
ext_idle_notification_obj = None


# swayidle
def __swayidle_running():
    return swayidle_process is not None and swayidle_process.poll() is None


def __start_swayidle_monitor():
    global swayidle_process
    global swayidle_start
    global swayidle_idle
    global swayidle_active
    logging.debug("Starting swayidle subprocess")
    swayidle_process = subprocess.Popen(
        ["swayidle", "timeout", "1", "date +S%s", "resume", "date +R%s"],
        stdout=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        encoding="utf-8",
    )
    for line in swayidle_process.stdout:
        with swayidle_lock:
            typ = line[0]
            timestamp = int(line[1:])
            if typ == "S":
                swayidle_idle = timestamp
            elif typ == "R":
                swayidle_active = timestamp


def __stop_swayidle_monitor():
    if __swayidle_running():
        logging.debug("Stopping swayidle subprocess")
        swayidle_process.terminate()


def __swayidle_idle_time():
    with swayidle_lock:
        if not __swayidle_running():
            utility.start_thread(__start_swayidle_monitor)
        # Idle more recently than active, meaning idle time isn't stale.
        if swayidle_idle > swayidle_active:
            idle_time = int(datetime.datetime.now().timestamp()) - swayidle_idle
            return idle_time
    return 0


# ext idle
def __start_ext_idle_monitor():
    global ext_idle_notification_obj

    from .ext_idle_notify import ExtIdleNotify

    ext_idle_notification_obj = ExtIdleNotify()
    ext_idle_notification_obj.run()


def __stop_ext_idle_monitor():
    global ext_idle_notification_obj

    with ext_idle_notify_lock:
        if ext_idle_notification_obj is not None:
            ext_idle_notification_obj.stop()
            ext_idle_notification_obj = None


def __ext_idle_idle_time():
    global ext_idle_notification_obj
    with ext_idle_notify_lock:
        if ext_idle_notification_obj is None:
            __start_ext_idle_monitor()
        else:
            return ext_idle_notification_obj.get_idle_time_seconds()
    return 0


# gnome
def __gnome_wayland_idle_time():
    """Determine system idle time in seconds, specifically for gnome with
    wayland.

    If there's a failure, return 0.
    https://unix.stackexchange.com/a/492328/222290
    """
    try:
        output = subprocess.check_output(
            [
                "dbus-send",
                "--print-reply",
                "--dest=org.gnome.Mutter.IdleMonitor",
                "/org/gnome/Mutter/IdleMonitor/Core",
                "org.gnome.Mutter.IdleMonitor.GetIdletime",
            ]
        )
        return int(re.search(rb"\d+$", output).group(0)) / 1000
    except BaseException as e:
        logging.warning("Failed to get system idle time for gnome/wayland.")
        logging.warning(str(e))
        return 0


def __system_idle_time():
    """Get system idle time in minutes.

    Return the idle time if xprintidle is available, otherwise return 0.
    """
    try:
        if is_wayland_and_gnome:
            return __gnome_wayland_idle_time()
        elif use_swayidle:
            return __swayidle_idle_time()
        elif use_ext_idle_notify:
            return __ext_idle_idle_time()
        # Convert to seconds
        return int(subprocess.check_output(["xprintidle"]).decode("utf-8")) / 1000
    except BaseException:
        return 0


def __is_active():
    """Thread safe function to see if this plugin is active or not."""
    is_active = False
    with lock:
        is_active = active
    return is_active


def __set_active(is_active):
    """Thread safe function to change the state of the plugin."""
    global active
    with lock:
        active = is_active


def init(ctx, safeeyes_config, plugin_config):
    """Initialize the plugin."""
    global context
    global enable_safeeyes
    global disable_safeeyes
    global postpone
    global idle_time
    global short_break_interval
    global long_break_duration
    global waiting_time
    global postpone_if_active
    global is_wayland_and_gnome
    global use_swayidle
    global use_ext_idle_notify
    logging.debug("Initialize Smart Pause plugin")
    context = ctx
    enable_safeeyes = context["api"]["enable_safeeyes"]
    disable_safeeyes = context["api"]["disable_safeeyes"]
    postpone = context["api"]["postpone"]
    idle_time = plugin_config["idle_time"]
    postpone_if_active = plugin_config["postpone_if_active"]
    short_break_interval = (
        safeeyes_config.get("short_break_interval") * 60
    )  # Convert to seconds
    long_break_duration = safeeyes_config.get("long_break_duration")
    waiting_time = min(2, idle_time)  # If idle time is 1 sec, wait only 1 sec
    is_wayland_and_gnome = context["desktop"] == "gnome" and context["is_wayland"]
    use_swayidle = context["desktop"] == "sway"
    use_ext_idle_notify = (
        context["is_wayland"] and not use_swayidle and not is_wayland_and_gnome
    )


def __start_idle_monitor():
    """Continuously check the system idle time and pause/resume Safe Eyes based
    on it.
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
            if system_idle_time >= idle_time and context["state"] == State.WAITING:
                smart_pause_activated = True
                idle_start_time = datetime.datetime.now() - datetime.timedelta(
                    seconds=system_idle_time
                )
                logging.info("Pause Safe Eyes due to system idle")
                disable_safeeyes(None, True)
            elif (
                system_idle_time < idle_time
                and context["state"] == State.RESTING
                and idle_start_time is not None
            ):
                logging.info("Resume Safe Eyes due to user activity")
                smart_pause_activated = False
                idle_period = datetime.datetime.now() - idle_start_time
                idle_seconds = idle_period.total_seconds()
                context["idle_period"] = idle_seconds
                if idle_seconds < short_break_interval:
                    # Credit back the idle time
                    if next_break_time is not None:
                        # This method runs in a thread since the start.
                        # It may run before next_break is initialized in the
                        # update_next_break method
                        next_break = next_break_time + idle_period
                        enable_safeeyes(next_break.timestamp())
                    else:
                        enable_safeeyes()
                else:
                    # User is idle for more than the time between two breaks
                    enable_safeeyes()


def on_start():
    """Start a thread to continuously call xprintidle."""
    global active
    if not __is_active():
        # If SmartPause is already started, do not start it again
        logging.debug("Start Smart Pause plugin")
        __set_active(True)
        utility.start_thread(__start_idle_monitor)


def on_stop():
    """Stop the thread from continuously calling xprintidle."""
    global active
    global smart_pause_activated
    if smart_pause_activated:
        # Safe Eyes is stopped due to system idle
        smart_pause_activated = False
        return
    logging.debug("Stop Smart Pause plugin")
    if use_swayidle:
        __stop_swayidle_monitor()
    __set_active(False)
    idle_condition.acquire()
    idle_condition.notify_all()
    idle_condition.release()

    if use_ext_idle_notify:
        __stop_ext_idle_monitor()


def update_next_break(break_obj, dateTime):
    """Update the next break time."""
    global next_break_time
    global next_break_duration
    next_break_time = dateTime
    next_break_duration = break_obj.duration


def on_start_break(break_obj):
    """Lifecycle method executes just before the break."""
    if postpone_if_active:
        # Postpone this break if the user is active
        system_idle_time = __system_idle_time()
        if system_idle_time < 2:
            postpone(2)  # Postpone for 2 seconds


def disable():
    """SmartPause plugin was active earlier but now user has disabled it."""
    # Remove the idle_period
    context.pop("idle_period", None)
