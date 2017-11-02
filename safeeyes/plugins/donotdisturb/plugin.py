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
Skip Fullscreen plugin skips the break if the active window is fullscreen.
NOTE: Do not remove the unused import 'GdkX11' becuase it is required in Ubuntu 14.04
"""

import logging
import re
import subprocess

import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk
from gi.repository import GdkX11  # noqa F401

context = None
skip_break_window_classes = []
take_break_window_classes = []
unfullscreen_allowed = True


def is_active_window_skipped():
    """
    Check for full-screen applications.
    This method must be executed by the main thread. If not, it will cause to random failure.
    """
    logging.info('Searching for full-screen application')
    screen = Gdk.Screen.get_default()

    active_window = screen.get_active_window()
    if active_window:
        active_xid = str(active_window.get_xid())
        cmdlist = ['xprop', '-root', '-notype', '-id', active_xid, 'WM_CLASS', '_NET_WM_STATE']

        try:
            stdout = subprocess.check_output(cmdlist).decode('utf-8')
        except subprocess.CalledProcessError:
            logging.warning('Error in finding full-screen application')
        else:
            if stdout:
                is_fullscreen = 'FULLSCREEN' in stdout
                # Extract the process name
                process_names = re.findall('"(.+?)"', stdout)
                if process_names:
                    process = process_names[1].lower()
                    if process in skip_break_window_classes:
                        return True
                    elif process in take_break_window_classes:
                        if is_fullscreen and unfullscreen_allowed:
                            try:
                                active_window.unfullscreen()
                            except BaseException:
                                logging.error('Error in unfullscreen the window ' + process)
                        return False

                return is_fullscreen

    return False


def init(ctx, safeeyes_config, plugin_config):
    global context
    global skip_break_window_classes
    global take_break_window_classes
    global unfullscreen_allowed
    logging.debug('Initialize Skip Fullscreen plugin')
    context = ctx
    skip_break_window_classes = plugin_config['skip_break_windows'].split()
    take_break_window_classes = plugin_config['take_break_windows'].split()
    unfullscreen_allowed = plugin_config['unfullscreen']


def on_start_break(break_obj):
    """
    """
    return is_active_window_skipped()
