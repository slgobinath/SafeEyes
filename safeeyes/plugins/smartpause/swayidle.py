# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2025  Mel Dafert <m@dafert.at>

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

import logging
import math
import subprocess
import threading
import typing

from safeeyes import utility

from .interface import IdleMonitorInterface


class IdleMonitorSwayidle(IdleMonitorInterface):
    """IdleMonitorInterface implementation for swayidle."""

    swayidle_process: typing.Optional[subprocess.Popen] = None
    swayidle_lock = threading.Lock()
    swayidle_idle = 0
    swayidle_active = 0

    def init(self) -> None:
        pass

    def start_monitor(
        self,
        on_idle: typing.Callable[[], None],
        on_resumed: typing.Callable[[], None],
        idle_time: float,
    ) -> None:
        """Start watching for idling.

        This is run on the main thread, and should not block.
        """
        if not self.is_monitor_running():
            utility.start_thread(
                self._start_swayidle_monitor,
                on_idle=on_idle,
                on_resumed=on_resumed,
                idle_time=idle_time,
            )

    def is_monitor_running(self) -> bool:
        return (
            self.swayidle_process is not None and self.swayidle_process.poll() is None
        )

    def _start_swayidle_monitor(
        self,
        on_idle: typing.Callable[[], None],
        on_resumed: typing.Callable[[], None],
        idle_time: float,
    ) -> None:
        was_idle = False

        logging.debug("Starting swayidle subprocess")

        timeout = str(math.ceil(idle_time))

        self.swayidle_process = subprocess.Popen(
            [
                "swayidle",
                "timeout",
                timeout,
                "date +S%s",
                "resume",
                "date +R%s",
            ],
            stdout=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
            encoding="utf-8",
        )
        for line in self.swayidle_process.stdout:  # type: ignore[union-attr]
            with self.swayidle_lock:
                typ = line[0]
                timestamp = int(line[1:])
                if typ == "S":
                    self.swayidle_idle = timestamp
                    if not was_idle:
                        was_idle = True
                        utility.execute_main_thread(on_idle)
                elif typ == "R":
                    self.swayidle_active = timestamp
                    if was_idle:
                        was_idle = False
                        utility.execute_main_thread(on_resumed)

    def stop_monitor(self) -> None:
        """Stop watching for idling.

        This is run on the main thread. It may block a short time for cleanup.
        """
        if self.is_monitor_running() and self.swayidle_process is not None:
            logging.debug("Stopping swayidle subprocess")
            self.swayidle_process.terminate()
            self.swayidle_process.wait()
            self.swayidle_process = None

    def stop(self) -> None:
        pass
