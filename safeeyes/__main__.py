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
import argparse
import gettext
import signal

import gi

from safeeyes import SAFE_EYES_VERSION
from safeeyes import utility
from safeeyes.safeeyes import SafeEyes
from safeeyes.util import locale

gi.require_version('Gtk', '3.0')

gettext.install('safeeyes', utility.LOCALE_PATH)


def main():
    """
    Start the Safe Eyes.
    """
    system_locale = locale.init_locale()

    parser = argparse.ArgumentParser(prog='safeeyes', description=_('description'))
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-a', '--about', help=_('show the about dialog'), action='store_true')
    group.add_argument('-d', '--disable', help=_('disable the currently running safeeyes instance'),
                       action='store_true')
    group.add_argument('-e', '--enable', help=_('enable the currently running safeeyes instance'), action='store_true')
    group.add_argument('-q', '--quit', help=_('quit the running safeeyes instance and exit'), action='store_true')
    group.add_argument('-s', '--settings', help=_('show the settings dialog'), action='store_true')
    group.add_argument('-t', '--take-break', help=_('Take a break now').lower(), action='store_true')
    parser.add_argument('--debug', help=_('start safeeyes in debug mode'), action='store_true')
    parser.add_argument('--status', help=_('print the status of running safeeyes instance and exit'),
                        action='store_true')
    parser.add_argument('--version', action='version', version='%(prog)s ' + SAFE_EYES_VERSION)
    args = parser.parse_args()

    # Initialize the logging
    utility.intialize_logging(args.debug)
    utility.initialize_platform()

    safe_eyes = SafeEyes(system_locale)
    safe_eyes.run(args)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Handle Ctrl + C
    main()
