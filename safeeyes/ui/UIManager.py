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
import logging
from typing import Callable

from safeeyes.config import Config
from safeeyes.context import Context
from safeeyes.spi.api import WindowAPI
from safeeyes.thread import main
from safeeyes.ui.about_dialog import AboutDialog
from safeeyes.ui.settings_dialog import SettingsDialog


class UIManager(WindowAPI):

    def __init__(self, context: Context, on_config_changed: Callable[[Config], None]):
        self.__settings_dialog_visible = False
        self.__context = context
        self.__on_config_changed = on_config_changed

    @main
    def show_settings(self):
        """
        Listen to tray icon Settings action and send the signal to Settings dialog.
        """
        if not self.__settings_dialog_visible:
            logging.info("Show settings dialog")
            self.__settings_dialog_visible = True
            settings_dialog = SettingsDialog(self.__context, Config.from_json(), self.__save_settings)
            settings_dialog.show()

    @main
    def show_about(self):
        """
        Listen to tray icon About action and send the signal to About dialog.
        """
        logging.info("Show about dialog")
        about_dialog = AboutDialog(self.__context.version)
        about_dialog.show()

    def __save_settings(self, config: Config):
        """
        Listen to Settings dialog Save action and write to the config file.
        """
        self.__settings_dialog_visible = False

        if self.__context.config != config:
            # Config is modified
            self.__on_config_changed(config)
