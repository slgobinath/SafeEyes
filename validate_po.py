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

from collections import defaultdict
import os
import polib
import re
import sys

def has_equal_placeholders(left: str, right: str) -> bool:
    percents = re.finditer(r'%(?P<name>\(\w+\))?(?P<format>[a-z])', left)

    unnamed = defaultdict(int)
    named = []
    for percent in percents:
        if percent.group('name'):
            named.append(f"%({percent.group('name')}){percent.group('format')}")
        else:
            match = f"%{percent.group('format')}"
            unnamed[match] += 1

    # count unnamed cases (eg. %s, %d)
    for match, count in unnamed.items():
        if right.count(match) != count:
            return False

    # no need to count named cases - they are optional

    return True

def validate_po(locale: str, path: str) -> bool:
    success = True
    po = polib.pofile(path)
    for entry in po:
        if entry.msgstr and not has_equal_placeholders(entry.msgid, entry.msgstr):
            print("Number of variables mismatched in " + locale)
            print(entry.msgid + " -> " + entry.msgstr)
            print()
            success = False
        for plural in entry.msgstr_plural.values():
            if plural and not has_equal_placeholders(entry.msgid, plural):
                print("Number of variables mismatched in " + locale)
                print(entry.msgid + " -> " + plural)
                print()
                success = False
    return success

success = True
locales = os.listdir('safeeyes/config/locale')
for locale in sorted(locales):
    path = os.path.join('safeeyes/config/locale', locale, "LC_MESSAGES/safeeyes.po")
    if os.path.isfile(path):
        print('Validating translation %s...' % path)
        success = validate_po(locale, path) and success

sys.exit(0 if success else 1)
