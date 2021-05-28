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
import datetime
from typing import List

from safeeyes.context import Context
from safeeyes.plugin_utils.proxy import PluginProxy
from safeeyes.spi.api import PluginAPI
from safeeyes.spi.breaks import Break
from safeeyes.spi.plugin import TrayAction, Widget


class PluginManager(PluginAPI):

    def __init__(self, plugins: List[PluginProxy]):
        self.__plugins = plugins

    def init(self, context: Context) -> None:
        # PluginManager gets PluginProxy objects which internally have the config
        for plugin in self.__plugins:
            plugin.init(context, {})

    def is_break_allowed(self, break_obj: Break) -> bool:
        for plugin in self.__plugins:
            if not plugin.is_break_allowed(break_obj):
                return False
        return True

    def is_break_skipped(self, break_obj: Break) -> bool:
        for plugin in self.__plugins:
            if plugin.is_break_skipped(break_obj):
                return True
        return False

    def get_postpone_time(self, break_obj: Break) -> int:
        for plugin in self.__plugins:
            duration = plugin.get_postpone_time(break_obj)
            if duration > 0:
                return duration
        return -1

    def on_pre_break(self, break_obj: Break) -> None:
        for plugin in self.__plugins:
            plugin.on_pre_break(break_obj)

    def on_start_break(self, break_obj: Break) -> None:
        for plugin in self.__plugins:
            plugin.on_start_break(break_obj)

    def on_count_down(self, break_obj: Break, countdown: int, seconds: int) -> None:
        for plugin in self.__plugins:
            plugin.on_count_down(break_obj, countdown, seconds)

    def on_stop_break(self, break_obj: Break, skipped: bool, postponed: bool) -> None:
        for plugin in self.__plugins:
            plugin.on_stop_break(break_obj, skipped, postponed)

    def get_widgets(self, break_obj: Break) -> List[Widget]:
        widgets: List[Widget] = []
        for plugin in self.__plugins:
            widget = plugin.get_widget(break_obj)
            if widget is not None and not widget.is_empty():
                widgets.append(widget)
        return widgets

    def get_tray_actions(self, break_obj: Break) -> List[TrayAction]:
        actions = []
        for plugin in self.__plugins:
            action = plugin.get_tray_action(break_obj)
            if action is not None:
                actions.append(action)
        return actions

    def on_start(self) -> None:
        for plugin in self.__plugins:
            plugin.on_start()

    def on_stop(self) -> None:
        for plugin in self.__plugins:
            plugin.on_stop()

    def on_exit(self) -> None:
        for plugin in self.__plugins:
            plugin.on_exit()

    def update_next_break(self, break_obj: Break, next_short_break: datetime, next_long_break: datetime) -> None:
        for plugin in self.__plugins:
            plugin.update_next_break(break_obj, next_short_break, next_long_break)
