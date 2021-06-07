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

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import importlib.util
import os
import shutil
import subprocess
from typing import List, Optional

from safeeyes import SAFE_EYES_CONFIG_DIR, SAFE_EYES_HOME_DIR


def execute(command: List[str]) -> None:
    """
    Execute the shell command without waiting for its response.
    """
    if command:
        subprocess.Popen(command)


def module_exists(module: str) -> bool:
    """
    Check whether the given Python module exists.
    """
    result = importlib.util.find_spec(module)
    return bool(result)


def command_exists(command: str) -> bool:
    """
    Check whether the given command exist in the system or not.
    """
    if shutil.which(command):
        return True
    return False


def get_resource_path(resource_name: str) -> Optional[str]:
    """
    Return the user-defined resource if a system resource is overridden by the user.
    Otherwise, return the system resource. Return None if the specified resource does not exist.
    """
    if resource_name is None:
        return None
    resource_location = os.path.join(SAFE_EYES_CONFIG_DIR, 'resource', resource_name)
    if not os.path.isfile(resource_location):
        resource_location = os.path.join(SAFE_EYES_HOME_DIR, 'resource', resource_name)
        if not os.path.isfile(resource_location):
            # Resource not found
            return None

    return resource_location
