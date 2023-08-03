#!/usr/bin/env python3
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

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import polib

def validate_po(locale, path):
     po = polib.pofile(path)
     for entry in po:
         if entry.msgstr and (entry.msgid.count("%") != entry.msgstr.count("%")):
             print("Number of variables mismatched in " + locale)
             print(entry.msgid + " -> " + entry.msgstr)
             print()

locales = os.listdir('safeeyes/config/locale')
for locale in locales:
    path = os.path.join('safeeyes/config/locale', locale, "LC_MESSAGES/safeeyes.po")
    if os.path.isfile(path):
        validate_po(locale, path)