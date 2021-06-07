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
import datetime
from typing import List

from safeeyes.spi.breaks import BreakType, Break
from safeeyes.spi.plugin import Widget, TrayAction


class CoreAPI(abc.ABC):

    def __init__(self):
        self.__status: str = ''

    def set_status(self, message: str) -> None:
        self.__status = message

    def get_status(self) -> str:
        return self.__status

    def start(self, next_break_time: datetime = None, reset_breaks: bool = False):
        pass

    def stop(self):
        pass

    def quit(self):
        pass


class BreakAPI(abc.ABC):

    def has_breaks(self, break_type: BreakType = None) -> bool:
        pass

    def next_break(self) -> None:
        pass

    def skip(self) -> None:
        pass

    def postpone(self, duration: int) -> None:
        pass

    def schedule(self, next_break_time: datetime) -> None:
        pass

    def take_break(self, break_type: BreakType = None) -> None:
        pass


class WindowAPI(abc.ABC):

    def get_version(self) -> str:
        pass

    def show_settings(self):
        pass

    def show_about(self):
        pass


class PluginAPI(abc.ABC):

    def get_widgets(self, break_obj: Break) -> List[Widget]:
        pass

    def get_tray_actions(self, break_obj: Break) -> List[TrayAction]:
        pass


class Condition(abc.ABC):
    def hold(self, timeout: int) -> None:
        pass

    def release_all(self) -> None:
        pass


class ThreadAPI(abc.ABC):

    def release_all(self) -> None:
        pass

    def restart(self) -> None:
        pass

    def hold(self, timeout: int) -> None:
        pass

    def new_condition(self) -> Condition:
        pass
