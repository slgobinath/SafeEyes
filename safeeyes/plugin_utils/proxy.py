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
import inspect
import logging
from datetime import datetime
from typing import Optional, Any

from safeeyes.context import Context
from safeeyes.plugin_utils.error_repo import ErrorRepository
from safeeyes.plugin_utils.plugin import Plugin, Validator
from safeeyes.spi.breaks import Break
from safeeyes.spi.plugin import Widget, TrayAction, BreakAction


class ModuleUtil:
    @staticmethod
    def has_method(module, method_name, no_of_args=0):
        """
        Check whether the given function is defined in the module or not.
        """
        if hasattr(module, method_name):
            if len(inspect.getfullargspec(getattr(module, method_name)).args) == no_of_args:
                return True
        return False


class PluginProxy(Plugin):
    """
    A proxy class representing the actual plugin object.
    """

    def __init__(self, error_repo: ErrorRepository, plugin_id: str, plugin_module: Any, enabled: bool,
                 plugin_config: dict, plugin_settings: dict):
        self.__error_repo = error_repo
        self.__id: str = plugin_id
        self.__plugin = plugin_module
        self.__enabled: bool = enabled
        self.__config: dict = plugin_config
        self.__settings = plugin_settings

    def get_id(self) -> str:
        return self.__id

    def is_enabled(self) -> bool:
        return self.__enabled

    def __is_supported(self, break_obj: Break):
        if self.__enabled:
            return True
        else:
            return self.__config.get("break_override_allowed", False) and break_obj.is_plugin_enabled(self.__id)

    def can_breaks_override(self) -> bool:
        return self.__config.get("break_override_allowed", False)

    def disable(self) -> None:
        if self.__enabled:
            self.__enabled = False
            if ModuleUtil.has_method(self.__plugin, "disable", 0):
                logging.debug("Disable the plugin '%s'", self.__id)
                try:
                    self.__plugin.disable()
                except BaseException:
                    self.__error_repo.log_error(self.__id, "Error in disabling the plugin")
                    logging.exception("Error in disabling the plugin: %s", self.__id)

    def enable(self) -> None:
        if not self.__enabled:
            if self.__error_repo.has_error(self.__id):
                # Plugin was disabled due to an error
                return
            self.__enabled = True
            if ModuleUtil.has_method(self.__plugin, "enable", 0):
                logging.debug("Enable the plugin '%s'", self.__id)
                try:
                    self.__plugin.enable()
                except BaseException:
                    self.__enabled = False
                    self.__error_repo.log_error(self.__id, "Error in enabling the plugin")
                    logging.exception("Error in enabling the plugin: %s", self.__id)

    def update_settings(self, plugin_settings: dict) -> None:
        self.__settings = plugin_settings

    def init(self, context: Context, config: dict) -> None:
        """
        This function is called to initialize the plugin.
        """
        if ModuleUtil.has_method(self.__plugin, "init", 2):
            logging.debug("Init the plugin '%s'", self.__id)
            try:
                self.__plugin.init(context, self.__settings)
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in initializing the plugin")
                logging.exception("Error in initializing the plugin: %s", self.__id)

    def get_break_action(self, break_obj: Break) -> Optional[BreakAction]:
        """
        This function is called before on_pre_break and on_start_break.
        """
        if self.__is_supported(break_obj) and ModuleUtil.has_method(self.__plugin, "get_break_action", 1):
            logging.debug("Get break action from the plugin '%s'", self.__id)
            try:
                return self.__plugin.get_break_action(break_obj)
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in getting the break action")
                logging.exception("Error in getting the break action from: %s", self.__id)
        return BreakAction.allow()

    def on_pre_break(self, break_obj: Break) -> None:
        """
        Called some time before starting the break to prepare the plugins. For example, the notification plugin will
        show a notification during this method call.
        """
        if self.__is_supported(break_obj) and ModuleUtil.has_method(self.__plugin, "on_pre_break", 1):
            logging.debug("Call on_pre_break of the plugin '%s'", self.__id)
            try:
                self.__plugin.on_pre_break(break_obj)
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in calling on_pre_break")
                logging.exception("Error in calling on_pre_break from: %s", self.__id)

    def on_start_break(self, break_obj: Break) -> None:
        """
        Called when starting a break.
        """
        if self.__is_supported(break_obj) and ModuleUtil.has_method(self.__plugin, "on_start_break", 1):
            logging.debug("Call on_start_break of the plugin '%s'", self.__id)
            try:
                self.__plugin.on_start_break(break_obj)
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in calling on_start_break")
                logging.exception("Error in calling on_start_break from: %s", self.__id)

    def on_count_down(self, break_obj: Break, countdown: int, seconds: int) -> None:
        """
        Called during a break.
        """
        if self.__is_supported(break_obj) and ModuleUtil.has_method(self.__plugin, "on_count_down", 3):
            # Do not log the on_count_down function call as there will be too many entries
            try:
                self.__plugin.on_count_down(break_obj, countdown, seconds)
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in calling on_count_down")
                logging.exception("Error in calling on_count_down from: %s", self.__id)

    def on_stop_break(self, break_obj: Break, break_action: BreakAction) -> None:
        """
        Called when a break is stopped.
        """
        if self.__is_supported(break_obj) and ModuleUtil.has_method(self.__plugin, "on_stop_break", 2):
            logging.debug("Call on_stop_break of the plugin '%s'", self.__id)
            try:
                self.__plugin.on_stop_break(break_obj, break_action)
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in calling on_stop_break")
                logging.exception("Error in calling on_stop_break from: %s", self.__id)

    def get_widget(self, break_obj: Break) -> Optional[Widget]:
        """
        Return an optional break screen widget.
        """
        if self.__is_supported(break_obj) and ModuleUtil.has_method(self.__plugin, "get_widget", 1):
            logging.debug("Get widget from the plugin '%s'", self.__id)
            try:
                return self.__plugin.get_widget(break_obj)
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in getting the widget")
                logging.exception("Error in getting the widget from: %s", self.__id)
        return None

    def get_tray_action(self, break_obj: Break) -> Optional[TrayAction]:
        """
        Return an optional break screen widget.
        """
        if self.__is_supported(break_obj) and ModuleUtil.has_method(self.__plugin, "get_tray_action", 1):
            logging.debug("Get tray icon from the plugin '%s'", self.__id)
            try:
                return self.__plugin.get_tray_action(break_obj)
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in getting the tray action")
                logging.exception("Error in getting the tray action from: %s", self.__id)
        return None

    def on_start(self) -> None:
        """
        Called when Safe Eyes is started.
        """
        if self.__enabled and ModuleUtil.has_method(self.__plugin, "on_start", 0):
            logging.debug("Call on_start of the plugin '%s'", self.__id)
            try:
                self.__plugin.on_start()
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in calling on_start")
                logging.exception("Error in calling on_start from: %s", self.__id)

    def on_stop(self) -> None:
        """
        Called when Safe Eyes is stopped.
        """
        if self.__enabled and ModuleUtil.has_method(self.__plugin, "on_stop", 0):
            logging.debug("Call on_stop of the plugin '%s'", self.__id)
            try:
                self.__plugin.on_stop()
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in calling on_stop")
                logging.exception("Error in calling on_stop from: %s", self.__id)

    def on_exit(self) -> None:
        """
        Called when Safe Eyes is closed.
        """
        if self.__enabled and ModuleUtil.has_method(self.__plugin, "on_exit", 0):
            logging.debug("Call on_exit of the plugin '%s'", self.__id)
            try:
                self.__plugin.on_exit()
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in calling on_exit")
                logging.exception("Error in calling on_exit from: %s", self.__id)

    def update_next_break(self, break_obj: Break, next_short_break: Optional[datetime],
                          next_long_break: Optional[datetime]) -> None:
        """
        Called when the next break is scheduled.
        """
        if self.__is_supported(break_obj) and ModuleUtil.has_method(self.__plugin, "update_next_break", 3):
            logging.debug("Call update_next_break of the plugin '%s'", self.__id)
            try:
                self.__plugin.update_next_break(break_obj, next_short_break, next_long_break)
            except BaseException:
                self.__enabled = False
                self.__error_repo.log_error(self.__id, "Error in updating the next break")
                logging.exception("Error in updating the next break in: %s", self.__id)

    def execute_if_exists(self, func_name: str, *args, **kwargs) -> Optional[Any]:
        if self.__enabled and hasattr(self.__plugin, func_name):
            logging.debug("Call %s of the plugin '%s'", func_name, self.__id)
            function = getattr(self.__plugin, func_name)
            return function(*args, **kwargs)
        return None


class ValidatorProxy(Validator):

    def __init__(self, module: Any):
        self.__validator = module

    def validate(self, context: Context, plugin_config: dict, plugin_settings: dict) -> Optional[str]:
        if ModuleUtil.has_method(self.__validator, "validate", 3):
            return self.__validator.validate(context, plugin_config, plugin_settings)
        return None
