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

import argparse
from collections import defaultdict
import glob
import os
import polib
import re
import sys
import subprocess


def xgettext() -> str:
    def _xgettext(files: list, lang: str) -> str:
        return subprocess.check_output(
            [
                "xgettext",
                "--language",
                lang,
                "--sort-by-file",
                "--no-wrap",
                "-d",
                "safeeyes",
                "--no-location",
                "--omit-header",
                "-o",
                "-",
                "--",
                *files,
            ]
        ).decode()

    files_py = glob.glob("safeeyes/**/*.py", recursive=True)
    files_glade = glob.glob("safeeyes/**/*.glade", recursive=True)

    output = _xgettext(files_py, "Python")
    output = output + _xgettext(files_glade, "Glade")

    return output


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


def get_placeholders(message: str) -> tuple:
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


def ensure_named_placeholders(message: str) -> bool:
    (unnamed, named) = get_placeholders(message)
    return len(unnamed) == 0


def validate_pot() -> bool:
    success = True

    new_pot_contents = xgettext()
    new_pot = polib.pofile(new_pot_contents)
    old_pot = polib.pofile("safeeyes/config/locale/safeeyes.pot")

    for new_entry in new_pot:
        if old_pot.find(new_entry.msgid) is None:
            print(f"missing entry in pot: '{new_entry.msgid}'")
            success = False
        if not validate_placeholders(new_entry.msgid):
            success = False
        if new_entry.msgid_plural:
            if not (
                ensure_named_placeholders(new_entry.msgid)
                and ensure_named_placeholders(new_entry.msgid_plural)
            ):
                print(
                    f"Plural message must use named placeholders: '{new_entry.msgid}'"
                )
                success = False

    return success


def has_equal_placeholders(left: str, right: str) -> bool:
    (left_unnamed, left_named) = get_placeholders(left)
    (right_unnamed, right_named) = get_placeholders(right)

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


def validate_po_files() -> bool:
    success = True

    locales = os.listdir("safeeyes/config/locale")
    for locale in sorted(locales):
        path = os.path.join("safeeyes/config/locale", locale, "LC_MESSAGES/safeeyes.po")
        if os.path.isfile(path):
            print("Validating translation %s..." % path)
            success = validate_po(locale, path) and success

    return success


def validate():
    success = True
    success = validate_pot() and success
    success = validate_po_files() and success
    sys.exit(0 if success else 1)


def extract():
    success = True
    new_pot_contents = xgettext()
    new_pot = polib.pofile(new_pot_contents)
    pot_on_disk = polib.pofile("safeeyes/config/locale/safeeyes.pot", wrapwidth=0)

    for new_entry in new_pot:
        if not validate_placeholders(new_entry.msgid):
            success = False
        if pot_on_disk.find(new_entry.msgid) is None:
            pot_on_disk.append(new_entry)

    if success:
        pot_on_disk.save()

    sys.exit(0 if success else 1)


def main():
    parser = argparse.ArgumentParser(prog="validate_po")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--validate", action="store_const", dest="mode", const="validate"
    )
    group.add_argument(
        "--extract",
        help="Extract strings to pot file",
        action="store_const",
        dest="mode",
        const="extract",
    )
    parser.set_defaults(mode="validate")
    args = parser.parse_args()

    if args.mode == "validate":
        validate()
    elif args.mode == "extract":
        extract()


if __name__ == "__main__":
    main()
