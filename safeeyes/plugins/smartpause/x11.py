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

import subprocess
import threading
import typing

from safeeyes import utility

from .interface import IdleMonitorInterface


class IdleMonitorX11(IdleMonitorInterface):
    """IdleMonitorInterface implementation for X11.

    Note that this is quite inefficient. It polls every 2 seconds whether the user is
    idle or not, keeping the CPU active a lot.
    """

    active: bool = False
    lock = threading.Lock()
    idle_condition = threading.Condition()

    def _is_active(self) -> bool:
        """Thread safe function to see if this plugin is active or not."""
        is_active = False
        with self.lock:
            is_active = self.active
        return is_active

    def _set_active(self, is_active: bool) -> None:
        """Thread safe function to change the state of the plugin."""
        with self.lock:
            self.active = is_active

    def init(self) -> None:
        pass

    def start_monitor(
        self,
        on_idle: typing.Callable[[], None],
        on_resumed: typing.Callable[[], None],
        idle_time: float,
    ) -> None:
        """Start a thread to continuously call xprintidle."""
        if not self._is_active():
            # If SmartPause is already started, do not start it again
            self._set_active(True)
            utility.start_thread(
                self._start_idle_monitor,
                on_idle=on_idle,
                on_resumed=on_resumed,
                idle_time=idle_time,
            )

    def is_monitor_running(self) -> bool:
        return self._is_active()

    def _start_idle_monitor(
        self,
        on_idle: typing.Callable[[], None],
        on_resumed: typing.Callable[[], None],
        idle_time: float,
    ) -> None:
        """Continuously check the system idle time and pause/resume Safe Eyes based
        on it.
        """
        waiting_time = min(idle_time, 2)
        was_idle = False

        while self._is_active():
            # Wait for waiting_time seconds
            self.idle_condition.acquire()
            self.idle_condition.wait(waiting_time)
            self.idle_condition.release()

            if self._is_active():
                # Get the system idle time
                system_idle_time = (
                    # Convert to seconds
                    int(subprocess.check_output(["xprintidle"]).decode("utf-8")) / 1000
                )
                if system_idle_time >= idle_time and not was_idle:
                    was_idle = True
                    utility.execute_main_thread(on_idle)
                elif system_idle_time < idle_time and was_idle:
                    was_idle = False
                    utility.execute_main_thread(on_resumed)

    def stop_monitor(self) -> None:
        """Stop the thread from continuously calling xprintidle."""
        self._set_active(False)
        self.idle_condition.acquire()
        self.idle_condition.notify_all()
        self.idle_condition.release()

    def stop(self) -> None:
        pass
