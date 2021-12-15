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

from collections import defaultdict
from typing import Optional

from safeeyes.util.locale import get_text as _


class ErrorRepository:

    def __init__(self):
        self.__errors = defaultdict(list)

    def log_error(self, plugin_id: str, error_msg: str) -> None:
        self.__errors[plugin_id].append(error_msg)

    def has_error(self, plugin_id) -> bool:
        return self.__errors.get(plugin_id) is not None

    def get_error(self, plugin_id) -> Optional[str]:
        errors = self.__errors.get(plugin_id)
        if errors is None:
            return None
        elif len(errors) == 1:
            return _(errors[0])
        elif len(errors) > 1:
            return _('More than one errors found.')
        else:
            return None

    def clean(self) -> None:
        self.__errors = defaultdict(list)
