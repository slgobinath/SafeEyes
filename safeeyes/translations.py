#!/usr/bin/env python
# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2024 Mel Dafert <m@dafert.at>

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
"""Translation setup and helpers."""

import locale
import gettext
import sys
from safeeyes import utility

_translations = gettext.NullTranslations()


def setup():
    global _translations
    _translations = gettext.translation(
        "safeeyes",
        localedir=utility.LOCALE_PATH,
        languages=[utility.system_locale(), "en_US"],
        fallback=True,
    )
    try:
        # locale.bindtextdomain is required for Glade files
        locale.bindtextdomain("safeeyes", utility.LOCALE_PATH)
    except AttributeError:
        print(
            "installed python's gettext module does not support locale.bindtextdomain."
            " locale.bindtextdomain is required for Glade files",
            file=sys.stderr,
        )

    return _translations


def translate(message: str) -> str:
    """Translate the message using the current translator."""
    return _translations.gettext(message)
