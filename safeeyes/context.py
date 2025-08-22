# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2025 Mel Dafert <m@dafert.at>

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

from collections.abc import MutableMapping
import datetime
import typing

from safeeyes import utility
from safeeyes.model import BreakType, State

if typing.TYPE_CHECKING:
    from safeeyes.safeeyes import SafeEyes


class API:
    _application: "SafeEyes"

    def __init__(
        self,
        application: "SafeEyes",
    ) -> None:
        self._application = application

    def __getitem__(self, key: str) -> typing.Callable:
        """This is soft-deprecated - it is preferred to access the property."""
        return getattr(self, key)

    def show_settings(self, activation_token: typing.Optional[str] = None) -> None:
        utility.execute_main_thread(self._application.show_settings, activation_token)

    def show_about(self, activation_token: typing.Optional[str] = None) -> None:
        utility.execute_main_thread(self._application.show_about, activation_token)

    def enable_safeeyes(self, next_break_time=-1) -> None:
        utility.execute_main_thread(self._application.enable_safeeyes, next_break_time)

    def disable_safeeyes(self, status=None, is_resting=False) -> None:
        utility.execute_main_thread(
            self._application.disable_safeeyes, status, is_resting
        )

    def status(self) -> str:
        return self._application.status()

    def quit(self) -> None:
        utility.execute_main_thread(self._application.quit)

    def take_break(self, break_type: typing.Optional[BreakType] = None) -> None:
        utility.execute_main_thread(self._application.take_break, break_type)

    def has_breaks(self, break_type=None) -> bool:
        return self._application.safe_eyes_core.has_breaks(break_type)

    def postpone(self, duration=-1) -> None:
        self._application.safe_eyes_core.postpone(duration)

    def get_break_time(self, break_type=None) -> typing.Optional[datetime.datetime]:
        return self._application.safe_eyes_core.get_break_time(break_type)


class Context(MutableMapping):
    version: str
    api: API
    desktop: str
    is_wayland: bool
    locale: str
    session: dict[str, typing.Any]
    state: State

    skipped: bool = False
    postponed: bool = False
    skip_button_disabled: bool = False
    postpone_button_disabled: bool = False

    ext: dict

    def __init__(
        self,
        api: API,
        locale: str,
        version: str,
        session: dict[str, typing.Any],
    ) -> None:
        self.version = version
        self.desktop = utility.desktop_environment()
        self.is_wayland = utility.is_wayland()
        self.locale = locale
        self.session = session
        self.state = State.START
        self.api = api

        self.ext = {}

    def __setitem__(self, key: str, value: typing.Any) -> None:
        """This is soft-deprecated - it is preferred to access the property."""
        if hasattr(self, key):
            setattr(self, key, value)
            return

        self.ext[key] = value

    def __getitem__(self, key: str) -> typing.Any:
        """This is soft-deprecated - it is preferred to access the property."""
        if hasattr(self, key):
            return getattr(self, key)

        return self.ext[key]

    def __delitem__(self, key: str) -> None:
        """This is soft-deprecated - it is preferred to access the property."""
        if hasattr(self, key):
            raise Exception("cannot delete property")

        del self.ext[key]

    def __len__(self) -> int:
        """This is soft-deprecated."""
        return len(self.ext)

    def __iter__(self) -> typing.Iterator[typing.Any]:
        """This is soft-deprecated."""
        return iter(self.ext)
