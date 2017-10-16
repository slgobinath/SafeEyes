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

from safeeyes import Utility


class Break(object):
    """
    An entity class which represents a break.
    """
    def __init__(self, break_type, name, time, image, plugins):
        self.type = break_type
        self.name = name
        self.time = time
        self.image = image
        self.plugins = plugins

    def __str__(self):
        return 'Break: {{name: "{}", type: {}, time: {}}}\n'.format(self.name, self.type, self.time)

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
