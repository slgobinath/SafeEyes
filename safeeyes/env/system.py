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
import pwd
import shutil
import subprocess
from typing import List, Optional

import psutil

from safeeyes import SAFE_EYES_CONFIG_DIR, SAFE_EYES_HOME_DIR
from safeeyes.env.desktop import DesktopEnvironment


class Environment:

    def __init__(self):
        self.desktop: DesktopEnvironment = DesktopEnvironment.get_env()
        self.user: str = Environment.__get_username()
        self.found_another_safe_eyes = Environment.__is_another_safe_eyes_running()

    @staticmethod
    def __get_username():
        return pwd.getpwuid(os.getuid())[0]

    @staticmethod
    def __is_another_safe_eyes_running() -> bool:
        """
        Check if Safe Eyes is already running.
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
                if ("python3" in cmd_line[0] or "python" in cmd_line[0]) and (
                        "safeeyes" in cmd_line[1] or "safeeyes" in cmd_line):
                    process_count += 1
                    if process_count > 1:
                        return True

            # Ignore if process does not exist or does not have command line args
            except (IndexError, psutil.NoSuchProcess):
                pass
        return False


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
    resource_location = os.path.join(SAFE_EYES_CONFIG_DIR, "resource", resource_name)
    if not os.path.isfile(resource_location):
        resource_location = os.path.join(SAFE_EYES_HOME_DIR, "resource", resource_name)
        if not os.path.isfile(resource_location):
            # Resource not found
            return None

    return resource_location
