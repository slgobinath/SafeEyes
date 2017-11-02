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
import locale
import logging
import signal
import sys
from threading import Timer

import gi
import psutil
from safeeyes import Utility
from safeeyes.model import Config
from safeeyes.SafeEyes import SafeEyes
from safeeyes.SafeEyes import SAFE_EYES_VERSION
from safeeyes.rpc import RPCClient

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

gettext.install('safeeyes', Utility.LOCALE_PATH)


def __running():
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


def __evaluate_arguments(args, safe_eyes):
    """
    Evaluate the arguments and execute the operations.
    """
    if args.about:
        Utility.execute_main_thread(safe_eyes.show_about)
    elif args.disable:
        Utility.execute_main_thread(safe_eyes.disable_safeeyes)
    elif args.enable:
        Utility.execute_main_thread(safe_eyes.enable_safeeyes)
    elif args.settings:
        Utility.execute_main_thread(safe_eyes.show_settings)
    elif args.take_break:
        Utility.execute_main_thread(safe_eyes.take_break)


def main():
    """
    Start the Safe Eyes.
    """
    system_locale = gettext.translation('safeeyes', localedir=Utility.LOCALE_PATH, languages=[Utility.system_locale(), 'en_US'], fallback=True)
    system_locale.install()
    # locale.bindtextdomain is required for Glade files
    # gettext.bindtextdomain(gettext.textdomain(), Utility.LOCALE_PATH)
    locale.bindtextdomain('safeeyes', Utility.LOCALE_PATH)

    parser = argparse.ArgumentParser(prog='safeeyes', description=_('description'))
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-a', '--about', help=_('show the about dialog'), action='store_true')
    group.add_argument('-d', '--disable', help=_('disable the currently running safeeyes instance'), action='store_true')
    group.add_argument('-e', '--enable', help=_('enable the currently running safeeyes instance'), action='store_true')
    group.add_argument('-q', '--quit', help=_('quit the running safeeyes instance and exit'), action='store_true')
    group.add_argument('-s', '--settings', help=_('show the settings dialog'), action='store_true')
    group.add_argument('-t', '--take-break', help=_('Take a break now').lower(), action='store_true')
    parser.add_argument('--debug', help=_('start safeeyes in debug mode'), action='store_true')
    parser.add_argument('--version', action='version', version='%(prog)s ' + SAFE_EYES_VERSION)
    args = parser.parse_args()

    # Initialize the logging
    Utility.intialize_logging(args.debug)
    config = Config()

    if __running():
        logging.info("Safe Eyes is already running")
        rpc_client = RPCClient(config.get('rpc_port'))
        if args.about:
            rpc_client.show_about()
        elif args.disable:
            rpc_client.disable_safeeyes()
        elif args.enable:
            rpc_client.enable_safeeyes()
        elif args.settings:
            rpc_client.show_settings()
        elif args.take_break:
            rpc_client.take_break()
        elif args.quit:
            rpc_client.quit()
        else:
            # Default behavior is opening settings
            rpc_client.show_settings()
        sys.exit(0)
    elif not args.quit:
        logging.info("Starting Safe Eyes")
        safeeyes = SafeEyes(system_locale, config)
        safeeyes.start()
        Timer(1.0, lambda: __evaluate_arguments(args, safeeyes)).start()
        Gtk.main()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)    # Handle Ctrl + C
    main()
