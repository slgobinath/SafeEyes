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

def validate_placeholders(message: str) -> bool:
    pos = 0

    success = True

    count_placeholders = 0
    count_unnamed = 0

    while True:
        index = message.find("%", pos)
        if index == -1:
            break

        pos = index + 1

        nextchar = message[pos : pos + 1]

        name = None

        if nextchar == "(":
            index = message.find(")", pos)
            if index == -1:
                success = False
                print(f"Unclosed parenthetical in '{message}'")
                break
            name = message[pos + 1 : index]

            pos = index + 1

        nextchar = message[pos : pos + 1]
        if nextchar not in ["%", "s", "d", "i", "f", "F"]:
            success = False
            print(f"Invalid format modifier in '{message}'")
            break

        if nextchar != "%":
            count_placeholders += 1
            if name is None:
                count_unnamed += 1

        pos += 1
        continue

    if count_unnamed > 1:
        success = False
        print(f"Multiple unnamed placeholders in '{message}'")

    if count_unnamed > 0 and count_placeholders > count_unnamed:
        success = False
        print(f"Mixing named and unnamed placeholders in '{message}'")

    return success

def has_equal_placeholders(left: str, right: str) -> bool:
    def _get_placeholders(message: str) -> tuple:
        percents = re.finditer(r"%(?P<name>\(\w+\))?(?P<format>[a-z])", message)

        unnamed = defaultdict(int)
        named = set()
        for percent in percents:
            if percent.group("name"):
                named.add(f"%({percent.group('name')}){percent.group('format')}")
            else:
                match = f"%{percent.group('format')}"
                unnamed[match] += 1
        return (unnamed, named)

    (left_unnamed, left_named) = _get_placeholders(left)
    (right_unnamed, right_named) = _get_placeholders(right)

    # count unnamed cases (eg. %s, %d)
    for match, count in left_unnamed.items():
        if right_unnamed.get(match, 0) != count:
            return False

    # named cases are optional - but ensure that translation does not add new ones
    if not right_named.issubset(left_named):
        return False

    return True

def validate_po(locale: str, path: str) -> bool:
    success = True
    po = polib.pofile(path)
    for entry in po:
        if entry.msgstr:
            if not validate_placeholders(entry.msgstr):
                success = False
            if not has_equal_placeholders(entry.msgid, entry.msgstr):
                print("Number of variables mismatched in " + locale)
                print(entry.msgid + " -> " + entry.msgstr)
                print()
                success = False
        for plural in entry.msgstr_plural.values():
            if plural:
                if not validate_placeholders(plural):
                    success = False
                if not has_equal_placeholders(entry.msgid, plural):
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
