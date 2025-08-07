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
"""Audible Alert plugin plays a sound after each breaks to notify the user that
the break has end.
"""

import logging
from safeeyes import utility

context = None
pre_break_alert = False
post_break_alert = False
volume: int = 100


def play_sound(resource_name):
    """Play the audio resource.

    Arguments:
    ---------
        resource_name {string} -- name of the wav file resource

    """
    global volume

    logging.info("Playing audible alert %s at volume %s%%", resource_name, volume)
    try:
        # Open the sound file
        path = utility.get_resource_path(resource_name)
        if path is None:
            return
    except BaseException:
        logging.error("Failed to load resource %s", resource_name)
        return

    if utility.command_exist("ffplay"):  # ffmpeg
        utility.execute_command(
            "ffplay",
            [
                path,
                "-nodisp",
                "-nostats",
                "-hide_banner",
                "-autoexit",
                "-volume",
                str(volume),
            ],
        )
    elif utility.command_exist("pw-play"):  # pipewire
        pwvol = volume / 100  # 0 = silent, 1.0 = 100% volume
        utility.execute_command("pw-play", ["--volume", str(pwvol), path])


def init(ctx, safeeyes_config, plugin_config):
    """Initialize the plugin."""
    global context
    global pre_break_alert
    global post_break_alert
    global volume
    logging.debug("Initialize Audible Alert plugin")
    context = ctx
    pre_break_alert = plugin_config["pre_break_alert"]
    post_break_alert = plugin_config["post_break_alert"]
    volume = int(plugin_config.get("volume", 100))
    if volume > 100:
        volume = 100
    if volume < 0:
        volume = 0


def on_pre_break(break_obj):
    """Play the pre_break sound if the option is enabled.

    Arguments:
    ---------
        break_obj {safeeyes.model.Break} -- the break object

    """
    if pre_break_alert:
        play_sound("on_pre_break.wav")


def on_stop_break():
    """After the break, play the alert sound."""
    # Do not play if the break is skipped or postponed
    if context["skipped"] or context["postponed"] or not post_break_alert:
        return
    play_sound("on_stop_break.wav")
