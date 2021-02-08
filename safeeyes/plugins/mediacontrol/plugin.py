#!/usr/bin/env python
# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2019  Gobinath

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
Media Control plugin lets users to pause currently playing media player from the break screen.
"""

import logging
import os
import dbus
import re
import gi
from safeeyes.model import TrayAction
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

tray_icon_path = None


def __active_players():
    """
    List of all media players which are playing now.
    """
    players = []
    bus = dbus.SessionBus()

    for service in bus.list_names():
        if re.match('org.mpris.MediaPlayer2.', service):
            player = bus.get_object(service, "/org/mpris/MediaPlayer2")
            interface = dbus.Interface(player, 'org.freedesktop.DBus.Properties')
            status = str(interface.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')).lower()
            if status == "playing":
                players.append(player)
    return players


def __pause_players(players):
    """
    Pause all playing media players using dbus.
    """
    for player in players:
        interface = dbus.Interface(player, dbus_interface='org.mpris.MediaPlayer2.Player')
        interface.Pause()


def init(ctx, safeeyes_config, plugin_config):
    """
    Initialize the screensaver plugin.
    """
    global tray_icon_path
    tray_icon_path = os.path.join(plugin_config['path'], "resource/pause.png")


def get_tray_action(break_obj):
    """
    Return TrayAction only if there is a media player currently playing.
    """
    players = __active_players()
    if players:
        return TrayAction.build("Pause media",
                                tray_icon_path,
                                Gtk.STOCK_MEDIA_PAUSE,
                                lambda: __pause_players(players))
