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

from distutils.version import LooseVersion
from enum import Enum
import logging
from safeeyes import Utility


class Break(object):
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


class BreakQueue(object):

    def __init__(self, config, context):
        self.context = context
        self.__current_break = None
        self.__first_break = None
        self.__short_break_time = config.get('short_break_interval')
        self.__long_break_time = config.get('long_break_interval')
        self.__short_pointer = self.__build_queue(BreakType.SHORT_BREAK,
                                                  config.get('short_breaks'),
                                                  self.__short_break_time,
                                                  config.get('short_break_duration'))
        self.__long_pointer = self.__build_queue(BreakType.LONG_BREAK,
                                                 config.get('long_breaks'),
                                                 self.__long_break_time,
                                                 config.get('long_break_duration'))
        # Restore the last break from session
        if not self.is_empty():
            last_break = context['session'].get('break')
            if last_break is not None:
                current_break = self.get_break()
                if last_break != current_break.name:
                    pointer = self.next()
                    while(pointer != current_break and pointer.name != last_break):
                        pointer = self.next()

    def get_break(self):
        if self.__current_break is None:
            self.__current_break = self.next()
        return self.__current_break

    def is_long_break(self):
        return self.__current_break is not None and self.__current_break.type == BreakType.LONG_BREAK

    def next(self):
        if self.is_empty():
            return None
        break_obj = None
        if self.__short_pointer is None:
            # No short breaks
            break_obj = self.__long_pointer
            self.context['break_type'] = 'long'
            # Update the pointer to next
            self.__long_pointer = self.__long_pointer.next
        elif self.__long_pointer is None:
            # No long breaks
            break_obj = self.__short_pointer
            self.context['break_type'] = 'short'
            # Update the pointer to next
            self.__short_pointer = self.__short_pointer.next
        elif self.__long_pointer.time <= self.__short_pointer.time:
            # Time for a long break
            break_obj = self.__long_pointer
            self.context['break_type'] = 'long'
            # Update the pointer to next
            self.__long_pointer = self.__long_pointer.next
        else:
            # Time for a short break
            break_obj = self.__short_pointer
            self.context['break_type'] = 'short'
            # Reduce the break time from the next long break
            self.__long_pointer.time -= self.__short_pointer.time
            # Update the pointer to next
            self.__short_pointer = self.__short_pointer.next

        if self.__first_break is None:
            self.__first_break = break_obj
        self.context['new_cycle'] = self.__first_break == break_obj
        if self.__current_break is not None:
            # Reset the time of long breaks
            if self.__current_break.type == BreakType.LONG_BREAK:
                self.__current_break.time = self.__long_break_time

        self.__current_break = break_obj
        self.context['session']['break'] = self.__current_break.name

        return break_obj

    def is_empty(self):
        return self.__short_pointer is None and self.__long_pointer is None

    def __build_queue(self, break_type, break_configs, break_time, break_duration):
        """
        Build a circular queue of breaks.
        """
        head = None
        tail = None
        for break_config in break_configs:
            name = _(break_config['name'])
            duration = break_config.get('duration', break_duration)
            image = break_config.get('image')
            plugins = break_config.get('plugins', None)
            interval = break_config.get('interval', break_time)

            # Validate time value
            if not isinstance(duration, int) or duration <= 0:
                logging.error('Invalid break duration in: ' + str(break_config))
                continue

            break_obj = Break(break_type, name, interval, duration, image, plugins)
            if head is None:
                head = break_obj
                tail = break_obj
            else:
                tail.next = break_obj
                tail = break_obj

        # Connect the tail to the head
        if tail is not None:
            tail.next = head
        return head


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


class EventHook(object):
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


class Config(object):
    """
    The configuration of Safe Eyes.
    """

    def __init__(self):
        # Read the config files
        self.__user_config = Utility.load_json(Utility.CONFIG_FILE_PATH)
        self.__system_config = Utility.load_json(Utility.SYSTEM_CONFIG_FILE_PATH)
        self.__force_upgrade = ['long_breaks', 'short_breaks']

        if self.__user_config is None:
            Utility.initialize_safeeyes()
            self.__user_config = self.__system_config
            self.save()
        else:
            system_config_version = self.__system_config['meta']['config_version']
            meta_obj = self.__user_config.get('meta', None)
            if meta_obj is None:
                # Corrupted user config
                self.__user_config = self.__system_config
            else:
                user_config_version = str(meta_obj.get('config_version', '0.0.0'))
                if LooseVersion(user_config_version) != LooseVersion(system_config_version):
                    # Update the user config
                    self.__merge_dictionary(self.__user_config, self.__system_config)
                    self.__user_config = self.__system_config
                    # Update the style sheet
                    Utility.replace_style_sheet()

        Utility.merge_plugins(self.__user_config)
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

    def save(self):
        """
        Save the configuration to file.
        """
        Utility.write_json(Utility.CONFIG_FILE_PATH, self.__user_config)

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


class TrayAction(object):
    """
    Data object wrapping name, icon and action.
    """

    def __init__(self, name, icon, action):
        self.name = name
        self.icon = icon
        self.action = action

    @classmethod
    def build(cls, name, icon_path, icon_id, action):
        image = Utility.load_and_scale_image(icon_path, 12, 12)
        if image is None:
            return TrayAction(name, icon_id, action)
        else:
            image.show()
            return TrayAction(name, image, action)
