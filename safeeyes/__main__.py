#!/usr/bin/env python3
# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2016  Gobinath

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
Safe Eyes is a utility to remind you to take break frequently to protect your eyes from eye strain.
"""

import gettext
import locale
import logging
import sys

import gi
import psutil
from safeeyes import Utility
from safeeyes.SafeEyes import SafeEyes

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

gettext.install('safeeyes', Utility.LOCALE_PATH)

SAFE_EYES_VERSION = "2.0.0"


def running():
    """
    Check if SafeEyes is already running.
    """
    process_count = 0
    for proc in psutil.process_iter():
        if not proc.cmdline:
            continue
        try:
            # Check if safeeyes is in process arguments
            if callable(proc.cmdline):
                # Latest psutil has cmdline function
                cmd_line = proc.cmdline()
            else:
                # In older versions cmdline was a list object
                cmd_line = proc.cmdline
            if ('python3' in cmd_line[0] or 'python' in cmd_line[0]) and ('safeeyes' in cmd_line[1] or 'safeeyes' in cmd_line):
                process_count += 1
                if process_count > 1:
                    return True

        # Ignore if process does not exist or does not have command line args
        except (IndexError, psutil.NoSuchProcess):
            pass
    return False


def main():
    """
    Start the Safe Eyes.
    """
    # Initialize the logging
    Utility.intialize_logging()

    logging.info("Starting Safe Eyes")

    if not running():
        system_locale = gettext.translation('safeeyes', localedir=Utility.LOCALE_PATH, languages=[Utility.system_locale(), 'en_US'], fallback=True)
        system_locale.install()
        # locale.bindtextdomain is required for Glade files
        locale.bindtextdomain('safeeyes', Utility.LOCALE_PATH)
        safeeyes = SafeEyes(system_locale)
        safeeyes.start()
        Gtk.main()
    else:
        logging.info('Another instance of safeeyes is already running')
        sys.exit(0)


if __name__ == '__main__':
    main()
