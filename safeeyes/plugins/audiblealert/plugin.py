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
Audible Alert plugin plays a sound after each breaks to notify the user that the break has end.
"""

import logging

from safeeyes import utility
from safeeyes.context import Context
from safeeyes.env import system
from safeeyes.spi.breaks import Break


class Player:

    def __init__(self, config: dict):
        self.__pre_break_enabled: bool = config.get('pre_break_alert', False)
        self.__post_break_enabled: bool = config.get('post_break_alert', False)

    def play_pre_break(self) -> None:
        if self.__pre_break_enabled:
            Player.__play('on_pre_break.wav')

    def play_stop_break(self) -> None:
        if self.__post_break_enabled:
            Player.__play('on_stop_break.wav')

    @staticmethod
    def __play(resource: str) -> None:
        logging.info('Audible Alert: playing audio %s', resource)
        # Open the sound file
        path = utility.get_resource_path(resource)
        if path is not None:
            system.execute(['aplay', '-q', path])


player: Player


def init(ctx: Context, plugin_config: dict) -> None:
    """
    Initialize the plugin.
    """
    global player
    logging.info('Audible Alert: initialize the plugin')
    player = Player(plugin_config)


def on_pre_break(break_obj: Break) -> None:
    """
    Play the pre_break sound if the option is enabled.
    """
    player.play_pre_break()


def on_stop_break(break_obj: Break, skipped: bool, postponed: bool) -> None:
    """
    After the break, play the alert sound
    """
    # Do not play if the break is skipped or postponed
    if skipped or postponed:
        return
    player.play_stop_break()
