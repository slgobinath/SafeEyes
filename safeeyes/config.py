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

from distutils.version import LooseVersion

from safeeyes import utility


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

    @staticmethod
    def from_json():
        """
        Create a fresh config from the json files.
        """
        config = Config(init=False)
        return config

    def save(self) -> None:
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

    def set(self, key, value) -> None:
        """
        Set the value.
        """
        self.__user_config[key] = value

    def get_session(self) -> dict:
        if self.get('persist_state'):
            return utility.open_session()
        else:
            return {'plugin': {}}

    def __eq__(self, config):
        return self.__user_config == config.__user_config

    def __ne__(self, config):
        return self.__user_config != config.__user_config
