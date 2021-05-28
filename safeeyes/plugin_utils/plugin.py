#!/usr/bin/env python
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

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import abc
from typing import Optional

from safeeyes.context import Context
from safeeyes.spi.breaks import Break
from safeeyes.spi.plugin import Widget, TrayAction


class Plugin(abc.ABC):
    def init(self, context: Context, config: dict) -> None:
        """
        This function is called to initialize the plugin.
        """
        pass

    def is_break_allowed(self, break_obj: Break) -> bool:
        """
        This function is called right before the pre-break and start break calls.
        Plugins must implement this function if they want to skip a break.
        """
        return True

    def is_break_skipped(self, break_obj: Break) -> bool:
        """
        his function is called right after calling the is_break_allowed function if the output of
        is_break_allowed is False. Plugins can return `True` if they want to skip the break and move to the next break.
        If the output is `False`, the get_postpone_time function will be called.
        """
        return False

    def get_postpone_time(self, break_obj: Break) -> int:
        """
        This function is called right after calling the is_break_skipped function if the output of
        is_break_skipped is False. Plugins can return a positive time in millis to postpone the break.
        Zero or negative value indicates that the plugin doesn't want to postpone the break which
        in turns will postpone the current break by a duration equivalent to the interval.
        """
        return -1

    def on_pre_break(self, break_obj: Break) -> None:
        """
        Called some time before starting the break to prepare the plugins. For example, the notification plugin will
        show a notification during this method call.
        """
        pass

    def on_start_break(self, break_obj: Break) -> None:
        """
        Called when starting a break.
        """
        pass

    def on_count_down(self, break_obj: Break, countdown: int, seconds: int) -> None:
        """
        Called during a break.
        """
        pass

    def on_stop_break(self, break_obj: Break, skipped: bool, postponed: bool) -> None:
        """
        Called when a break is stopped.
        """
        pass

    def get_widget(self, break_obj: Break) -> Optional[Widget]:
        """
        Return an optional break screen widget.
        """
        return None

    def get_tray_action(self, break_obj: Break) -> Optional[TrayAction]:
        """
        Return an optional break screen widget.
        """
        return None

    def on_start(self) -> None:
        """
        Called when Safe Eyes is started.
        """
        pass

    def on_stop(self) -> None:
        """
        Called when Safe Eyes is stopped.
        """
        pass

    def on_exit(self) -> None:
        """
        Called when Safe Eyes is closed.
        """
        pass

    def update_next_break(self, break_obj: Break, next_short_break: int, next_long_break: int) -> None:
        """
        Called when the next break is scheduled.
        """
        pass
