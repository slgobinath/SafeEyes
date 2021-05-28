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
from typing import Any

from safeeyes import SAFE_EYES_VERSION
from safeeyes.config import Config
from safeeyes.spi.api import CoreAPI, BreakAPI, WindowAPI, PluginAPI
from safeeyes.spi.state import State
from safeeyes.util.env import DesktopEnvironment

SESSION_KEY_BREAK = 'break'
SESSION_KEY_BREAK_TYPE = 'break_type'


class Context:

    def __init__(self, config: Config, locale):
        self.version: str = SAFE_EYES_VERSION
        self.config: Config = config
        self.locale = locale
        self.session: dict = config.get_session()
        self.state = State.START
        self.__settings_dialog_visible = False
        self.__env: DesktopEnvironment = DesktopEnvironment.get_env()
        self.core_api: CoreAPI = None
        self.break_api: BreakAPI = None
        self.window_api: WindowAPI = None
        self.plugin_api: PluginAPI = None

    def set_apis(self, core_api: CoreAPI, window_api: WindowAPI, break_api: BreakAPI, plugin_api: PluginAPI) -> None:
        self.core_api = core_api
        self.break_api = break_api
        self.plugin_api = plugin_api
        self.window_api = window_api

    def env(self) -> DesktopEnvironment:
        return self.__env

    def set_session(self, key: str, value: Any) -> None:
        self.session[key] = value

    def get_session(self, key: str) -> Any:
        return self.session.get(key, None)
