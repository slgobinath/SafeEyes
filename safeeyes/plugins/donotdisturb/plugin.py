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
NOTE: Do not remove the unused import 'GdkX11' because it is required in Ubuntu 14.04
"""

import logging
import os
import re
import subprocess
from typing import Optional

import gi

from safeeyes.context import Context
from safeeyes.spi.breaks import Break
from safeeyes.spi.plugin import BreakAction
from safeeyes.spi.state import State

gi.require_version('Gdk', '3.0')
from gi.repository import Gdk
from gi.repository import GdkX11  # noqa F401


class SystemState:

    def __init__(self, ctx: Context, config: dict):
        self.__context = ctx
        self.__skip_break_window_classes = config['skip_break_windows'].split()
        self.__take_break_window_classes = config['take_break_windows'].split()
        self.__unfullscreen_allowed = config['unfullscreen']
        self.__dnd_while_on_battery = config['while_on_battery']

    def skip_break(self) -> bool:
        if self.__dnd_while_on_battery and SystemState.__is_on_battery():
            logging.debug("Do Not Disturb: skipping the break as the system is on battery")
            return True
        return self.__is_wayland_full_screen() if self.__context.env.is_wayland() else self.__is_xorg_full_screen()

    def __is_wayland_full_screen(self) -> bool:
        logging.debug('Do Not Disturb: searching for full-screen application in wayland')
        cmdlist = ['wlrctl', 'toplevel', 'find', 'state:fullscreen']
        try:
            process = subprocess.Popen(cmdlist, stdout=subprocess.PIPE)
            process.communicate()[0]
            if process.returncode == 0:
                return True
            elif process.returncode == 1:
                return False
            elif process.returncode == 127:
                logging.warning('Do Not Disturb: could not find wlrctl needed to detect fullscreen under wayland')
                return False
        except subprocess.CalledProcessError:
            logging.warning('Do Not Disturb: error in finding full-screen application')
        return False

    def __is_xorg_full_screen(self) -> bool:
        """
        Check for full-screen applications.
        This method must be executed by the main thread. If not, it will cause random failure.
        """
        logging.debug('Do Not Disturb: searching for full-screen application in xorg')
        screen = Gdk.Screen.get_default()

        active_window = screen.get_active_window()
        if active_window:
            active_xid = str(active_window.get_xid())
            cmdlist = ['xprop', '-root', '-notype', '-id',
                       active_xid, 'WM_CLASS', '_NET_WM_STATE']

            try:
                stdout = subprocess.check_output(cmdlist).decode('utf-8')
            except subprocess.CalledProcessError:
                logging.warning('Do Not Disturb: error in finding full-screen application')
            else:
                if stdout:
                    is_fullscreen = 'FULLSCREEN' in stdout
                    # Extract the process name
                    process_names = re.findall('"(.+?)"', stdout)
                    if process_names:
                        process = process_names[1].lower()
                        if process in self.__skip_break_window_classes:
                            return True
                        elif process in self.__take_break_window_classes:
                            if is_fullscreen and self.__unfullscreen_allowed and self.__context.state == State.BREAK:
                                # Unfullscreen a window only if the break is ready to be taken (not during pre_break state)
                                try:
                                    active_window.unfullscreen()
                                except BaseException:
                                    logging.error('Do Not Disturb: error in unfullscreen the window ' + process)
                            return False

                    return is_fullscreen

        return False

    @staticmethod
    def __is_on_battery():
        """
        Check if the computer is running on battery.
        """
        on_battery = False
        power_sources = os.listdir('/sys/class/power_supply')
        logging.debug('Do Not Disturb: looking for battery status in available power sources: %s' % str(power_sources))
        for power_source in power_sources:
            if 'BAT' in power_source:
                # Found battery
                battery_status = os.path.join(
                    '/sys/class/power_supply', power_source, 'status')
                if os.path.isfile(battery_status):
                    # Additional check to confirm that the status file exists
                    try:
                        with open(battery_status, 'r') as status_file:
                            status = status_file.read()
                            if status:
                                on_battery = 'discharging' in status.lower()
                    except BaseException:
                        logging.error('Failed to read %s' % battery_status)
                break
        return on_battery


system_state: SystemState


def init(ctx: Context, plugin_config: dict):
    logging.info('Do Not Disturb: initialize the plugin')
    global system_state
    system_state = SystemState(ctx, plugin_config)


def get_break_action(self, break_obj: Break) -> Optional[BreakAction]:
    """
    Called just before on_pre_break and on_start_break.
    This is the opportunity for plugins to skip/postpone a break.
    """
    return BreakAction.postpone() if system_state.skip_break() else BreakAction.allow()
