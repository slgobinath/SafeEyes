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

from safeeyes import SAFE_EYES_VERSION, utility
from safeeyes.config import Config
from safeeyes.env.desktop import DesktopEnvironment
from safeeyes.spi.api import CoreAPI, BreakAPI, WindowAPI, PluginAPI, ThreadAPI
from safeeyes.spi.state import State

SESSION_KEY_BREAK = 'break'
SESSION_KEY_BREAK_TYPE = 'break_type'


class Session:

    def __init__(self, read_from_disk: bool):
        self.__session: dict = utility.open_session() if read_from_disk else {'plugin': {}}

    def get_plugin(self, plugin_id: str) -> dict:
        if plugin_id not in self.__session['plugin']:
            self.__session['plugin'][plugin_id] = {}
        return self.__session['plugin'][plugin_id]

    def set_plugin(self, plugin_id: str, value: dict) -> None:
        self.__session['plugin'][plugin_id] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.__session.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.__session[key] = value

    def save(self, write_to_disk: bool) -> None:
        if write_to_disk:
            utility.write_json(utility.SESSION_FILE_PATH, self.__session)
        else:
            utility.delete(utility.SESSION_FILE_PATH)


class Context:

    def __init__(self, config: Config, locale):
        self.version: str = SAFE_EYES_VERSION
        self.config: Config = config
        self.locale = locale
        self.session: Session = Session(config.get('persist_state', False))
        self.state = State.START
        self.__settings_dialog_visible = False
        self.env: DesktopEnvironment = DesktopEnvironment.get_env()
        self.core_api: CoreAPI
        self.thread_api: ThreadAPI
        self.break_api: BreakAPI
        self.window_api: WindowAPI
        self.plugin_api: PluginAPI

    def set_apis(self, core_api: CoreAPI,
                 thread_api: ThreadAPI,
                 window_api: WindowAPI,
                 break_api: BreakAPI,
                 plugin_api: PluginAPI) -> None:
        self.core_api = core_api
        self.thread_api = thread_api
        self.break_api = break_api
        self.plugin_api = plugin_api
        self.window_api = window_api
