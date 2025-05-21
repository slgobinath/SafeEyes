# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2017  Gobinath

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

# This file is heavily inspired by https://github.com/juienpro/easyland/blob/efc26a0b22d7bdbb0f8436183428f7036da4662a/src/easyland/idle.py

import threading
import datetime
import os
import select
import typing

from pywayland.client import Display
from pywayland.protocol.wayland.wl_seat import WlSeat
from pywayland.protocol.ext_idle_notify_v1 import ExtIdleNotifierV1


class ExtIdleNotify:
    _ext_idle_notify_internal: typing.Optional["ExtIdleNotifyInternal"] = None
    _thread = None

    _r_channel_started: int
    _w_channel_started: int

    _r_channel_stop: int
    _w_channel_stop: int

    def __init__(self):
        self._r_channel_started, self._w_channel_started = os.pipe()
        self._r_channel_stop, self._w_channel_stop = os.pipe()

    def run(self):
        self._thread = threading.Thread(
            target=self._run, name="ExtIdleNotify", daemon=False
        )
        self._thread.start()

        result = os.read(self._r_channel_started, 1)

        if result == b"0":
            raise Exception("ext-idle-notify-v1 not supported")

    def _run(self):
        # Note that this creates a new connection to the wayland compositor.
        # This is not an issue per se, but does mean that the compositor sees this as
        # a new, separate client, that just happens to run in the same process as
        # the SafeEyes gtk application.
        # (This is not a problem, currently. swayidle does the same, it even runs in a
        # separate process.)
        # If in the future, a compositor decides to lock down ext-idle-notify-v1 to
        # clients somehow, and we need to share the connection to wl_display with gtk
        # (which might require some hacks, or FFI code), we might run into other issues
        # described in this mailing thread:
        # https://lists.freedesktop.org/archives/wayland-devel/2019-March/040344.html
        # The best thing would be, of course, for gtk to gain native support for
        # ext-idle-notify-v1.
        with Display() as display:
            self._ext_idle_notify_internal = ExtIdleNotifyInternal(
                display, self._r_channel_stop, self._w_channel_started
            )
            self._ext_idle_notify_internal.run()
            self._ext_idle_notify_internal = None

    def stop(self):
        # write anything, just to wake up the channel
        if self._thread is not None:
            os.write(self._w_channel_stop, b"!")
            self._thread.join()
            self._thread = None
            os.close(self._r_channel_stop)
            os.close(self._w_channel_stop)

            os.close(self._r_channel_started)
            os.close(self._w_channel_started)

    def get_idle_time_seconds(self):
        if self._ext_idle_notify_internal is None:
            return 0

        return self._ext_idle_notify_internal.get_idle_time_seconds()


class ExtIdleNotifyInternal:
    """This runs in the thread, and is only alive while the display exists.

    Split out into a separate object to simplify lifetime handling.
    """

    _idle_notifier: typing.Optional[ExtIdleNotifierV1] = None
    _display: Display
    _r_channel_stop: int
    _w_channel_started: int
    _seat: typing.Optional[WlSeat] = None

    _idle_since = None

    def __init__(
        self, display: Display, r_channel_stop: int, w_channel_started: int
    ) -> None:
        self._display = display
        self._r_channel_stop = r_channel_stop
        self._w_channel_started = w_channel_started

    def run(self) -> None:
        reg = self._display.get_registry()
        reg.dispatcher["global"] = self._global_handler

        self._display.roundtrip()

        while self._seat is None:
            self._display.dispatch(block=True)

        if self._idle_notifier is None:
            self._seat = None

            self._display.roundtrip()

            # communicate to the outer thread that the compositor does not
            # implement the ext-idle-notify-v1 protocol
            os.write(self._w_channel_started, b"0")

            return

        os.write(self._w_channel_started, b"1")

        timeout_sec = 1
        # note that the typing doesn't work correctly here - it always says that
        # get_idle_notification is not defined
        notification = self._idle_notifier.get_idle_notification(  # type: ignore[attr-defined]
            timeout_sec * 1000, self._seat
        )
        notification.dispatcher["idled"] = self._idle_notifier_handler
        notification.dispatcher["resumed"] = self._idle_notifier_resume_handler

        display_fd = self._display.get_fd()

        while True:
            self._display.flush()

            # this blocks until either there are new events in self._display
            # (retrieved using dispatch())
            # or until there are events in self._r_channel_stop - which means that
            # stop() was called
            # unfortunately, this seems like the best way to make sure that dispatch
            # doesn't block potentially forever (up to multiple seconds in my usage)
            read, _w, _x = select.select((display_fd, self._r_channel_stop), (), ())

            if self._r_channel_stop in read:
                # the channel was written to, which means stop() was called
                break

            if display_fd in read:
                self._display.dispatch(block=True)

        self._display.roundtrip()

        notification.destroy()

        self._display.roundtrip()

        self._seat = None
        self._idle_notifier = None

    def _global_handler(self, reg, id_num, iface_name, version):
        if iface_name == "wl_seat":
            self._seat = reg.bind(id_num, WlSeat, version)
        if iface_name == "ext_idle_notifier_v1":
            self._idle_notifier = reg.bind(id_num, ExtIdleNotifierV1, version)

    def _idle_notifier_handler(self, notification):
        self._idle_since = datetime.datetime.now()

    def _idle_notifier_resume_handler(self, notification):
        self._idle_since = None

    def get_idle_time_seconds(self):
        if self._idle_since is None:
            return 0

        result = datetime.datetime.now() - self._idle_since
        return result.total_seconds()
