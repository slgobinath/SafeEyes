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
"""
This module contains the entity classes used by Safe Eyes and its plugins.
"""

import logging
import random
from distutils.version import LooseVersion
from enum import Enum

from safeeyes import utility


class Break:
    """
    An entity class which represents a break.
    """

    def __init__(self, break_type, name, time, duration, image, plugins):
        self.type = break_type
        self.name = name
        self.duration = duration
        self.image = image
        self.plugins = plugins
        self.time = time
        self.next = None

    def __str__(self):
        return 'Break: {{name: "{}", type: {}, duration: {}}}\n'.format(self.name, self.type, self.duration)

    def __repr__(self):
        return str(self)

    def is_long_break(self):
        """
        Check whether this break is a long break.
        """
        return self.type == BreakType.LONG_BREAK

    def is_short_break(self):
        """
        Check whether this break is a short break.
        """
        return self.type == BreakType.SHORT_BREAK

    def plugin_enabled(self, plugin_id, is_plugin_enabled):
        """
        Check whether this break supports the given plugin.
        """
        if self.plugins:
            return plugin_id in self.plugins
        else:
            return is_plugin_enabled


class BreakType(Enum):
    """
    Type of Safe Eyes breaks.
    """
    SHORT_BREAK = 1
    LONG_BREAK = 2


class BreakQueue:
    def __init__(self, config, context):
        self.context = context
        self.__current_break = None
        self.__current_long = 0
        self.__current_short = 0
        self.__shorts_taken = 0
        self.__short_break_time = config.get('short_break_interval')
        self.__long_break_time = config.get('long_break_interval')
        self.__is_random_order = config.get('random_order')
        self.__config = config

        self.__build_longs()
        self.__build_shorts()


        # Interface guarantees that short_interval >= 1
        # And that long_interval is a multiple of short_interval
        short_interval = config.get('short_break_interval')
        long_interval  = config.get('long_break_interval')
        self.__cycle_len = int(long_interval / short_interval)
        # To count every long break as a cycle in .next() if there are no short breaks
        if self.__short_queue is None:
            self.__cycle_len = 1

        # Restore the last break from session
        if not self.is_empty():
            last_break = context['session'].get('break')
            if last_break is not None:
                current_break = self.get_break()
                if last_break != current_break.name:
                    brk = self.next()
                    while brk != current_break and brk.name != last_break:
                        brk = self.next()

    def get_break(self):
        if self.__current_break is None:
            self.__current_break = self.next()
        return self.__current_break

    def is_long_break(self):
        return self.__current_break is not None and self.__current_break.type == BreakType.LONG_BREAK

    def next(self):
        break_obj = None
        shorts = self.__short_queue
        longs  = self.__long_queue

        if self.is_empty():
            return None

        if shorts is None:
            break_obj = self.__next_long()
        elif longs is None:
            break_obj = self.__next_short()
        elif longs[self.__current_long].time <= shorts[self.__current_short].time:
            break_obj = self.__next_long()
        else:
            break_obj = self.__next_short()

        # Shorts and longs exist -> set cycle on every long
        if break_obj.type == BreakType.LONG_BREAK:
            self.context['new_cycle'] = True
            self.__shorts_taken = 0
        # Only shorts exist -> set cycle when enough short breaks pass
        elif self.__shorts_taken  == self.__cycle_len:
            self.context['new_cycle'] = True
            self.__shorts_taken = 0
        else:
            self.context['new_cycle'] = False

        if self.__current_break is not None:
            # Reset the time of long breaks
            if self.__current_break.type == BreakType.LONG_BREAK:
                self.__current_break.time = self.__long_break_time

        self.__current_break = break_obj
        self.context['session']['break'] = self.__current_break.name

        return break_obj

    def reset(self):
        for break_object in self.__short_queue:
            break_object.time = self.__short_break_time
        
        for break_object in self.__long_queue:
            break_object.time = self.__long_break_time

    def is_empty(self):
        return self.__short_queue is None and self.__long_queue is None

    def __next_short(self):
        longs  = self.__long_queue
        shorts = self.__short_queue
        break_obj = shorts[self.__current_short]
        self.context['break_type'] = 'short'
        # Reduce the break time from the next long break (default)
        if longs:
            longs[self.__current_long].time -= shorts[self.__current_short].time

        # Update the index to next
        self.__current_short = (self.__current_short + 1) % len(shorts)

        # Shuffle queue
        if self.__current_short == 0 and self.__is_random_order:
            self.__build_shorts()

        self.__shorts_taken += 1
        return break_obj

    def __next_long(self):
        longs  = self.__long_queue
        break_obj = longs[self.__current_long]
        self.context['break_type'] = 'long'

        # Update the index to next
        self.__current_long = (self.__current_long + 1) % len(longs)

        # Shuffle queue
        if self.__current_long == 0 and self.__is_random_order:
            self.__build_longs()

        return break_obj

    def __build_queue(self, break_type, break_configs, break_time, break_duration):
        """
        Build a queue of breaks.
        """
        size = len(break_configs)

        if 0 == size:
            # No breaks
            return None

        if self.__is_random_order:
            breaks_order = random.sample(break_configs, size)
        else:
            breaks_order = break_configs

        queue = [None] * size
        for i, break_config in enumerate(breaks_order):
            name = _(break_config['name'])
            duration = break_config.get('duration', break_duration)
            image = break_config.get('image')
            plugins = break_config.get('plugins', None)
            interval = break_config.get('interval', break_time)

            # Validate time value
            if not isinstance(duration, int) or duration <= 0:
                logging.error('Invalid break duration in: ' +
                              str(break_config))
                continue

            break_obj = Break(break_type, name, interval,
                              duration, image, plugins)
            queue[i] = break_obj

        return queue

    def __build_shorts(self):
        self.__short_queue = self.__build_queue(BreakType.SHORT_BREAK,
                                                  self.__config.get('short_breaks'),
                                                  self.__short_break_time,
                                                  self.__config.get('short_break_duration'))

    def __build_longs(self):
        self.__long_queue = self.__build_queue(BreakType.LONG_BREAK,
                                                 self.__config.get('long_breaks'),
                                                 self.__long_break_time,
                                                 self.__config.get('long_break_duration'))



class State(Enum):
    """
    Possible states of Safe Eyes.
    """
    START = 0,
    WAITING = 1,
    PRE_BREAK = 2,
    BREAK = 3,
    STOPPED = 4,
    QUIT = 5


class EventHook:
    """
    Hook to attach and detach listeners to system events.
    """

    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__handlers.remove(handler)
        return self

    def fire(self, *args, **keywargs):
        """
        Fire all listeners attached with.
        """
        for handler in self.__handlers:
            if not handler(*args, **keywargs):
                return False
        return True


class Config:
    """
    The configuration of Safe Eyes.
    """

    def __init__(self, init=True):
        # Read the config files
        self.__user_config = utility.load_json(utility.CONFIG_FILE_PATH)
        self.__system_config = utility.load_json(
            utility.SYSTEM_CONFIG_FILE_PATH)
        # If there any breaking changes in long_breaks, short_breaks or any other keys, use the __force_upgrade list
        self.__force_upgrade = []
        # self.__force_upgrade = ['long_breaks', 'short_breaks']

        if init:
            if self.__user_config is None:
                utility.initialize_safeeyes()
                self.__user_config = self.__system_config
                self.save()
            else:
                system_config_version = self.__system_config['meta']['config_version']
                meta_obj = self.__user_config.get('meta', None)
                if meta_obj is None:
                    # Corrupted user config
                    self.__user_config = self.__system_config
                else:
                    user_config_version = str(
                        meta_obj.get('config_version', '0.0.0'))
                    if LooseVersion(user_config_version) != LooseVersion(system_config_version):
                        # Update the user config
                        self.__merge_dictionary(
                            self.__user_config, self.__system_config)
                        self.__user_config = self.__system_config
                        # Update the style sheet
                        utility.replace_style_sheet()

            utility.merge_plugins(self.__user_config)
            self.save()

    def __merge_dictionary(self, old_dict, new_dict):
        """
        Merge the dictionaries.
        """
        for key in new_dict:
            if key == "meta" or key in self.__force_upgrade:
                continue
            if key in old_dict:
                new_value = new_dict[key]
                old_value = old_dict[key]
                if type(new_value) is type(old_value):
                    # Both properties have same type
                    if isinstance(new_value, dict):
                        self.__merge_dictionary(old_value, new_value)
                    else:
                        new_dict[key] = old_value

    def clone(self):
        config = Config(init=False)
        return config

    def save(self):
        """
        Save the configuration to file.
        """
        utility.write_json(utility.CONFIG_FILE_PATH, self.__user_config)

    def get(self, key, default_value=None):
        """
        Get the value.
        """
        value = self.__user_config.get(key, default_value)
        if value is None:
            value = self.__system_config.get(key, None)
        return value

    def set(self, key, value):
        """
        Set the value.
        """
        self.__user_config[key] = value

    def __eq__(self, config):
        return self.__user_config == config.__user_config

    def __ne__(self, config):
        return self.__user_config != config.__user_config


class TrayAction:
    """
    Data object wrapping name, icon and action.
    """

    def __init__(self, name, icon, action, system_icon):
        self.name = name
        self.__icon = icon
        self.action = action
        self.system_icon = system_icon
        self.__toolbar_buttons = []

    def get_icon(self):
        if self.system_icon:
            return self.__icon
        else:
            image = utility.load_and_scale_image(self.__icon, 16, 16)
            image.show()
            return image

    def add_toolbar_button(self, button):
        self.__toolbar_buttons.append(button)

    def reset(self):
        for button in self.__toolbar_buttons:
            button.hide()
        self.__toolbar_buttons.clear()

    @classmethod
    def build(cls, name, icon_path, icon_id, action):
        image = utility.load_and_scale_image(icon_path, 12, 12)
        if image is None:
            return TrayAction(name, icon_id, action, True)
        else:
            return TrayAction(name, icon_path, action, False)
