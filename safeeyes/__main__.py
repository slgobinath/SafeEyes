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
"""Safe Eyes is a utility to remind you to take break frequently to protect
your eyes from eye strain.
"""

import gettext
import locale
import signal
import sys

from safeeyes import utility
from safeeyes.model import Config
from safeeyes.safeeyes import SafeEyes

gettext.install("safeeyes", utility.LOCALE_PATH)


def main():
    """Start the Safe Eyes."""
    system_locale = gettext.translation(
        "safeeyes",
        localedir=utility.LOCALE_PATH,
        languages=[utility.system_locale(), "en_US"],
        fallback=True,
    )
    system_locale.install()
    try:
        # locale.bindtextdomain is required for Glade files
        locale.bindtextdomain("safeeyes", utility.LOCALE_PATH)
    except AttributeError:
        print(
            "installed python's gettext module does not support locale.bindtextdomain."
            " locale.bindtextdomain is required for Glade files",
            file=sys.stderr,
        )

    config = Config()

    safe_eyes = SafeEyes(system_locale, config)
    safe_eyes.run(sys.argv)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Handle Ctrl + C
    main()
