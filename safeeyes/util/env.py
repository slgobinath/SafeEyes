#!/usr/bin/env python
# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2021  Gobinath

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
import logging
import os
import re
import subprocess


class DesktopEnvironment:
    def __init__(self, name: str, display_server: str):
        self.name: str = name
        self.display_server: str = display_server

    @staticmethod
    def get_env():
        return DesktopEnvironment(DesktopEnvironment.__get_desktop_env(),
                                  "wayland" if DesktopEnvironment.__is_wayland() else "xorg")

    @staticmethod
    def __get_desktop_env() -> str:
        """
        Detect the desktop environment.
        """
        desktop_session = os.environ.get('DESKTOP_SESSION')
        current_desktop = os.environ.get('XDG_CURRENT_DESKTOP')
        env = 'unknown'
        if desktop_session is not None:
            desktop_session = desktop_session.lower()
            if desktop_session in ['gnome', 'unity', 'budgie-desktop', 'cinnamon', 'mate', 'xfce4', 'lxde', 'pantheon',
                                   'fluxbox', 'blackbox', 'openbox', 'icewm', 'jwm', 'afterstep', 'trinity', 'kde']:
                env = desktop_session
            elif desktop_session.startswith('xubuntu') or (current_desktop is not None and 'xfce' in current_desktop):
                env = 'xfce'
            elif desktop_session.startswith('lubuntu'):
                env = 'lxde'
            elif 'plasma' in desktop_session or desktop_session.startswith('kubuntu') or os.environ.get(
                    'KDE_FULL_SESSION') == 'true':
                env = 'kde'
            elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
                env = 'gnome'
            elif desktop_session.startswith('ubuntu'):
                env = 'unity'
        return env

    @staticmethod
    def __is_wayland() -> bool:
        """
        Determine if Wayland is running
        https://unix.stackexchange.com/a/325972/222290
        """
        try:
            session_id = subprocess.check_output(['loginctl']).split(b'\n')[1].split()[0]
            output = subprocess.check_output(['loginctl', 'show-session', session_id, '-p', 'Type'])
        except BaseException:
            logging.warning('Unable to determine if wayland is running. Assuming no.')
            return False
        else:
            return bool(re.search(b'wayland', output, re.IGNORECASE))
