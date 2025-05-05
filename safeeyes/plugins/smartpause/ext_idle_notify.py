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

from pywayland.client import Display
from pywayland.protocol.wayland.wl_seat import WlSeat
from pywayland.protocol.ext_idle_notify_v1 import ExtIdleNotifierV1


class ExtIdleNotify:
    _idle_notifier = None
    _seat = None
    _notification = None
    _notifier_set = False
    _running = True
    _thread = None
    _r_channel = None
    _w_channel = None

    _idle_since = None

    def __init__(self):
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
        self._display = Display()
        self._display.connect()
        self._r_channel, self._w_channel = os.pipe()

    def stop(self):
        self._running = False
        # write anything, just to wake up the channel
        os.write(self._w_channel, b"!")
        self._notification.destroy()
        self._notification = None
        self._seat = None
        self._thread.join()
        os.close(self._r_channel)
        os.close(self._w_channel)

    def run(self):
        self._thread = threading.Thread(
            target=self._run, name="ExtIdleNotify", daemon=False
        )
        self._thread.start()

    def _run(self):
        reg = self._display.get_registry()
        reg.dispatcher["global"] = self._global_handler

        display_fd = self._display.get_fd()

        while self._running:
            self._display.flush()

            # this blocks until either there are new events in self._display
            # (retrieved using dispatch())
            # or until there are events in self._r_channel - which means that stop()
            # was called
            # unfortunately, this seems like the best way to make sure that dispatch
            # doesn't block potentially forever (up to multiple seconds in my usage)
            read, _w, _x = select.select((display_fd, self._r_channel), (), ())

            if self._r_channel in read:
                # the channel was written to, which means stop() was called
                # at this point, self._running should be false as well
                break

            if display_fd in read:
                self._display.dispatch(block=True)

        self._display.disconnect()

    def _global_handler(self, reg, id_num, iface_name, version):
        if iface_name == "wl_seat":
            self._seat = reg.bind(id_num, WlSeat, version)
        if iface_name == "ext_idle_notifier_v1":
            self._idle_notifier = reg.bind(id_num, ExtIdleNotifierV1, version)

        if self._idle_notifier and self._seat and not self._notifier_set:
            self._notifier_set = True
            timeout_sec = 1
            self._notification = self._idle_notifier.get_idle_notification(
                timeout_sec * 1000, self._seat
            )
            self._notification.dispatcher["idled"] = self._idle_notifier_handler
            self._notification.dispatcher["resumed"] = (
                self._idle_notifier_resume_handler
            )

    def _idle_notifier_handler(self, notification):
        self._idle_since = datetime.datetime.now()

    def _idle_notifier_resume_handler(self, notification):
        self._idle_since = None

    def get_idle_time_seconds(self):
        if self._idle_since is None:
            return 0

        result = datetime.datetime.now() - self._idle_since
        return result.total_seconds()
