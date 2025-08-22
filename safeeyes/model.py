#!/usr/bin/env python
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
"""This module contains the entity classes used by Safe Eyes and its
plugins.
"""

import copy
import logging
import random
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Union
import typing

from packaging.version import parse

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from safeeyes import utility
from safeeyes.translations import translate as _

if typing.TYPE_CHECKING:
    from safeeyes.context import Context


class BreakType(Enum):
    """Type of Safe Eyes breaks."""

    SHORT_BREAK = 1
    LONG_BREAK = 2


class Break:
    """An entity class which represents a break."""

    type: BreakType
    name: str
    time: int
    duration: int
    image: typing.Optional[str]  # path
    plugins: dict

    def __init__(
        self,
        break_type: BreakType,
        name: str,
        time: int,
        duration: int,
        image: typing.Optional[str],
        plugins: dict,
    ):
        self.type = break_type
        self.name = name
        self.duration = duration
        self.image = image
        self.plugins = plugins
        self.time = time

    def __str__(self) -> str:
        return 'Break: {{name: "{}", type: {}, duration: {}}}\n'.format(
            self.name, self.type, self.duration
        )

    def __repr__(self) -> str:
        return str(self)

    def is_long_break(self) -> bool:
        """Check whether this break is a long break."""
        return self.type == BreakType.LONG_BREAK

    def is_short_break(self) -> bool:
        """Check whether this break is a short break."""
        return self.type == BreakType.SHORT_BREAK

    def plugin_enabled(self, plugin_id: str, is_plugin_enabled: bool) -> bool:
        """Check whether this break supports the given plugin."""
        if self.plugins:
            return plugin_id in self.plugins
        else:
            return is_plugin_enabled


class BreakQueue:
    __current_break: Break
    __current_long: int = 0
    __current_short: int = 0
    __short_break_time: int
    __long_break_time: int
    __is_random_order: bool
    __long_queue: typing.Optional[list[Break]]
    __short_queue: typing.Optional[list[Break]]
    context: "Context"

    @classmethod
    def create(
        cls, config: "Config", context: "Context"
    ) -> typing.Optional["BreakQueue"]:
        short_break_time = config.get("short_break_interval")
        long_break_time = config.get("long_break_interval")
        is_random_order = config.get("random_order")

        short_queue = cls.__build_queue(
            BreakType.SHORT_BREAK,
            config.get("short_breaks"),
            short_break_time,
            config.get("short_break_duration"),
            is_random_order,
        )

        long_queue = cls.__build_queue(
            BreakType.LONG_BREAK,
            config.get("long_breaks"),
            long_break_time,
            config.get("long_break_duration"),
            is_random_order,
        )

        if short_queue is None and long_queue is None:
            return None

        return cls(
            context,
            short_break_time,
            long_break_time,
            is_random_order,
            short_queue,
            long_queue,
        )

    def __init__(
        self,
        context: "Context",
        short_break_time: int,
        long_break_time: int,
        is_random_order: bool,
        short_queue: typing.Optional[list[Break]],
        long_queue: typing.Optional[list[Break]],
    ) -> None:
        """Constructor for BreakQueue. Do not call this directly.

        Instead, use BreakQueue.create() instead.
        short_queue and long_queue must not both be None, and must not be an empty
        list.
        """
        self.context = context
        self.__short_break_time = short_break_time
        self.__long_break_time = long_break_time
        self.__is_random_order = is_random_order
        self.__short_queue = short_queue
        self.__long_queue = long_queue

        # load first break
        self.__set_next_break()

        # Restore the last break from session
        last_break = context.session.get("break")
        if last_break is not None:
            current_break = self.get_break()
            if last_break != current_break.name:
                brk = self.next()
                while brk != current_break and brk.name != last_break:
                    brk = self.next()

    def get_break(self) -> Break:
        return self.__current_break

    def get_break_with_type(
        self, break_type: typing.Optional[BreakType] = None
    ) -> typing.Optional[Break]:
        if break_type is None or self.__current_break.type == break_type:
            return self.__current_break

        if break_type == BreakType.LONG_BREAK:
            if self.__long_queue is None:
                return None
            return self.__long_queue[self.__current_long]

        if self.__short_queue is None:
            return None
        return self.__short_queue[self.__current_short]

    def is_long_break(self) -> bool:
        return self.__current_break.type == BreakType.LONG_BREAK

    def next(self, break_type: typing.Optional[BreakType] = None) -> Break:
        """Advance to the next break, and return that break.

        If break_type is given, advance to the next break with that type.
        If the last break in the queue is reached, this resets the internal index to
        the first break again, and shuffle if needed.
        """
        shorts = self.__short_queue
        longs = self.__long_queue
        previous_break = self.__current_break

        # Reset break that has just ended
        if previous_break.is_long_break():
            previous_break.time = self.__long_break_time
            if self.__current_long == 0 and self.__is_random_order:
                # Shuffle queue
                if self.__long_queue is not None:
                    random.shuffle(self.__long_queue)
        else:
            # Reduce the break time from the next long break (default)
            if longs:
                if shorts is None:
                    raise Exception(
                        "this may not happen, either short or long breaks must be"
                        " defined"
                    )
                longs[self.__current_long].time -= shorts[self.__current_short].time
            if self.__current_short == 0 and self.__is_random_order:
                if self.__short_queue is not None:
                    random.shuffle(self.__short_queue)

        self.__set_next_break(break_type)

        return self.__current_break

    def __set_next_break(self, break_type: typing.Optional[BreakType] = None) -> None:
        shorts = self.__short_queue
        longs = self.__long_queue

        if shorts is None:
            break_obj = self.__next_long()
        elif longs is None:
            break_obj = self.__next_short()
        elif (
            break_type == BreakType.LONG_BREAK
            or longs[self.__current_long].time <= shorts[self.__current_short].time
        ):
            break_obj = self.__next_long()
        else:
            break_obj = self.__next_short()

        self.__current_break = break_obj
        self.context.session["break"] = self.__current_break.name

    def skip_long_break(self) -> None:
        if not (self.__short_queue and self.__long_queue):
            return

        for break_object in self.__short_queue:
            break_object.time = self.__short_break_time

        for break_object in self.__long_queue:
            break_object.time = self.__long_break_time

        if self.__current_break.type == BreakType.LONG_BREAK:
            # Note: this skips the long break, meaning the following long break
            # won't be the current one, but the next one after
            # we could decrement the __current_long counter, but then we'd need to
            # handle wraparound and possibly randomizing, which seems complicated
            self.__current_break = self.__next_short()
            self.context.session["break"] = self.__current_break.name

    def is_empty(self, break_type: BreakType) -> bool:
        """Check if the given break type is empty or not."""
        if break_type == BreakType.SHORT_BREAK:
            return self.__short_queue is None
        elif break_type == BreakType.LONG_BREAK:
            return self.__long_queue is None
        else:
            typing.assert_never(break_type)

    def __next_short(self) -> Break:
        shorts = self.__short_queue

        if shorts is None:
            raise Exception("this may only be called when there are short breaks")

        break_obj = shorts[self.__current_short]
        self.context.ext["break_type"] = "short"

        # Update the index to next
        self.__current_short = (self.__current_short + 1) % len(shorts)

        return break_obj

    def __next_long(self) -> Break:
        longs = self.__long_queue

        if longs is None:
            raise Exception("this may only be called when there are long breaks")

        break_obj = longs[self.__current_long]
        self.context.ext["break_type"] = "long"

        # Update the index to next
        self.__current_long = (self.__current_long + 1) % len(longs)

        return break_obj

    @staticmethod
    def __build_queue(
        break_type: BreakType,
        break_configs: list[dict],
        break_time: int,
        break_duration: int,
        is_random_order: bool,
    ) -> typing.Optional[list[Break]]:
        """Build a queue of breaks."""
        size = len(break_configs)

        if 0 == size:
            # No breaks
            return None

        if is_random_order:
            breaks_order = random.sample(break_configs, size)
        else:
            breaks_order = break_configs

        queue: list[Break] = []
        for break_config in breaks_order:
            name = _(break_config["name"])
            duration = break_config.get("duration", break_duration)
            image = break_config.get("image")
            plugins = break_config.get("plugins", None)
            interval = break_config.get("interval", break_time)

            # Validate time value
            if not isinstance(duration, int) or duration <= 0:
                logging.error("Invalid break duration in: " + str(break_config))
                continue

            break_obj = Break(break_type, name, interval, duration, image, plugins)
            queue.append(break_obj)

        if len(queue) == 0:
            return None

        return queue


class State(Enum):
    """Possible states of Safe Eyes."""

    START = (0,)  # Starting scheduler
    WAITING = (1,)  # User is working (waiting for next break)
    PRE_BREAK = (2,)  # Preparing for break
    BREAK = (3,)  # Break
    STOPPED = (4,)  # Disabled
    QUIT = (5,)  # Quitting
    RESTING = 6  # Resting (natural break)


class EventHook:
    """Hook to attach and detach listeners to system events."""

    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__handlers.remove(handler)
        return self

    def fire(self, *args, **keywargs):
        """Fire all listeners attached with."""
        for handler in self.__handlers:
            if not handler(*args, **keywargs):
                return False
        return True


class Config:
    """The configuration of Safe Eyes."""

    __user_config: dict[str, typing.Any]
    __system_config: dict[str, typing.Any]

    @classmethod
    def load(cls) -> "Config":
        # Read the config files
        user_config = utility.load_json(utility.CONFIG_FILE_PATH)
        system_config = utility.load_json(utility.SYSTEM_CONFIG_FILE_PATH)
        # If there any breaking changes in long_breaks, short_breaks or any other keys,
        # use the force_upgrade_keys list
        force_upgrade_keys: list[str] = []
        # force_upgrade_keys = ['long_breaks', 'short_breaks']

        # if create_startup_entry finds a broken autostart symlink, it will repair
        # it
        utility.create_startup_entry(force=False)
        if user_config is None:
            utility.initialize_safeeyes()
            user_config = copy.deepcopy(system_config)
            cfg = cls(user_config, system_config)
            cfg.save()
            return cfg
        else:
            system_config_version = system_config["meta"]["config_version"]
            meta_obj = user_config.get("meta", None)
            if meta_obj is None:
                # Corrupted user config
                user_config = copy.deepcopy(system_config)
            else:
                user_config_version = str(meta_obj.get("config_version", "0.0.0"))
                if parse(user_config_version) != parse(system_config_version):
                    # Update the user config
                    new_user_config = copy.deepcopy(system_config)
                    cls.__merge_dictionary(
                        user_config, new_user_config, force_upgrade_keys
                    )
                    user_config = new_user_config

        utility.merge_plugins(user_config)

        cfg = cls(user_config, system_config)
        cfg.save()
        return cfg

    def __init__(
        self,
        user_config: dict[str, typing.Any],
        system_config: dict[str, typing.Any],
    ):
        self.__user_config = user_config
        self.__system_config = system_config

    @classmethod
    def __merge_dictionary(cls, old_dict, new_dict, force_upgrade_keys: list[str]):
        """Merge the dictionaries."""
        for key in new_dict:
            if key == "meta" or key in force_upgrade_keys:
                continue
            if key in old_dict:
                new_value = new_dict[key]
                old_value = old_dict[key]
                if type(new_value) is type(old_value):
                    # Both properties have same type
                    if isinstance(new_value, dict):
                        cls.__merge_dictionary(old_value, new_value, force_upgrade_keys)
                    else:
                        new_dict[key] = old_value

    def clone(self) -> "Config":
        config = Config(
            user_config=copy.deepcopy(self.__user_config),
            system_config=self.__system_config,
        )
        return config

    def save(self) -> None:
        """Save the configuration to file."""
        utility.write_json(utility.CONFIG_FILE_PATH, self.__user_config)

    def get(self, key, default_value=None):
        """Get the value."""
        value = self.__user_config.get(key, default_value)
        if value is None:
            value = self.__system_config.get(key, None)
        return value

    def set(self, key, value):
        """Set the value."""
        self.__user_config[key] = value

    def __eq__(self, config):
        return self.__user_config == config.__user_config

    def __ne__(self, config):
        return self.__user_config != config.__user_config


class TrayAction:
    """Data object wrapping name, icon and action."""

    __toolbar_buttons: list[Gtk.Button]

    def __init__(
        self,
        name: str,
        icon: str,
        action: typing.Callable,
        system_icon: bool,
        single_use: bool,
    ) -> None:
        self.name = name
        self.__icon = icon
        self.action = action
        self.system_icon = system_icon
        self.__toolbar_buttons = []
        self.single_use = single_use

    def get_icon(self) -> Gtk.Image:
        if not self.system_icon:
            image = utility.load_and_scale_image(self.__icon, 16, 16)
            if image is not None:
                image.show()
                return image

        image = Gtk.Image.new_from_icon_name(self.__icon)
        return image

    def add_toolbar_button(self, button):
        self.__toolbar_buttons.append(button)

    def reset(self):
        for button in self.__toolbar_buttons:
            button.hide()
        self.__toolbar_buttons.clear()

    @classmethod
    def build(
        cls,
        name: str,
        icon_path: typing.Optional[str],
        icon_id: str,
        action: typing.Callable,
        single_use: bool = True,
    ) -> "TrayAction":
        if icon_path is not None:
            image = utility.load_and_scale_image(icon_path, 12, 12)
            if image is not None:
                return TrayAction(name, icon_path, action, False, single_use)

        return TrayAction(name, icon_id, action, True, single_use)


@dataclass
class PluginDependency:
    message: str
    link: Optional[str] = None
    retryable: bool = False


class RequiredPluginException(Exception):
    def __init__(
        self, plugin_id, plugin_name: str, message: Union[str, PluginDependency]
    ):
        if isinstance(message, PluginDependency):
            msg = message.message
        else:
            msg = message

        super().__init__(msg)

        self.plugin_id = plugin_id
        self.plugin_name = plugin_name
        self.message = message

    def get_plugin_id(self):
        return self.plugin_id

    def get_plugin_name(self):
        return self.plugin_name

    def get_message(self):
        return self.message
