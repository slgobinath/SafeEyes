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

from abc import ABC, abstractmethod
from typing import Callable


class IdleMonitorInterface(ABC):
    """Platform-specific interface to notify when the user is idle.

    The on_idle and on_resumed hooks must be used to notify safeeyes when the user
    has gone idle. The on_idle hook must be fired first, afterwards they must be called
    in alternation.
    They must be fired from the main thread.
    """

    @abstractmethod
    def init(self) -> None:
        """Initialize the monitor.

        This is called once initially.
        This is run on the main thread, and should only block for a short time for
        startup.
        """
        pass

    @abstractmethod
    def start_monitor(
        self,
        on_idle: Callable[[], None],
        on_resumed: Callable[[], None],
        idle_time: float,
    ) -> None:
        """Start watching for idling.

        This will be called multiple times, whenever the monitor should start watching
        or after configuration changes.
        This is run on the main thread, and should only block for a short time for
        startup.
        """
        pass

    @abstractmethod
    def is_monitor_running(self) -> bool:
        """Check if the monitor is running.

        This is run on the main thread, and should not block.
        """
        pass

    @abstractmethod
    def stop_monitor(self) -> None:
        """Stop watching for idling.

        This will be called multiple times, whenever the monitor should stop watching
        or when configuration changes.
        This is run on the main thread. It may block a short time for cleanup.
        """
        pass

    def configuration_changed(
        self,
        on_idle: Callable[[], None],
        on_resumed: Callable[[], None],
        idle_time: float,
    ) -> None:
        """Restart the idle watcher.

        This method will be called when configuration changes. It may be overridden
        by implementations for optimization.
        This is run on the main thread. It may block a short time for cleanup/startup.
        """
        self.stop_monitor()
        self.start_monitor(on_idle, on_resumed, idle_time)

    @abstractmethod
    def stop(self) -> None:
        """Deinitialize the monitor.

        This is called once before the monitor is destroyed.
        This is run on the main thread. It may block a short time for cleanup.
        """
        pass
