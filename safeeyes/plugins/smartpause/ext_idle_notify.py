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

import logging
import threading
import datetime

from pywayland.client import Display
from pywayland.protocol.wayland.wl_seat import WlSeat
from pywayland.protocol.ext_idle_notify_v1 import (
    ExtIdleNotificationV1,
    ExtIdleNotifierV1
)


class ExtIdleNotify:
    _idle_notifier = None
    _seat = None
    _notification = None
    _notifier_set = False
    _running = True
    _thread = None

    _idle_since = None

    def __init__(self):
        self._display = Display()
        self._display.connect()

    def stop(self):
        self._running = False
        self._notification.destroy()
        self._notification = None
        self._seat = None
        self._thread.join()

    def run(self):
        self._thread = threading.Thread(target=self._run, name="ExtIdleNotify", daemon=False)
        self._thread.start()

    def _run(self):
        reg = self._display.get_registry()
        reg.dispatcher['global'] = self._global_handler

        while self._running:
            self._display.dispatch(block=True)

        self._display.disconnect()

    def _global_handler(self, reg, id_num, iface_name, version):
        if iface_name == 'wl_seat':
            self._seat = reg.bind(id_num, WlSeat, version)
        if iface_name == "ext_idle_notifier_v1":
            self._idle_notifier = reg.bind(id_num, ExtIdleNotifierV1, version)

        if self._idle_notifier and self._seat and not self._notifier_set:
            self._notifier_set = True
            timeout_sec = 1
            self._notification = self._idle_notifier.get_idle_notification(timeout_sec * 1000, self._seat)
            self._notification.dispatcher['idled'] = self._idle_notifier_handler
            self._notification.dispatcher['resumed'] = self._idle_notifier_resume_handler

    def _idle_notifier_handler(self, notification):
        self._idle_since = datetime.datetime.now()

    def _idle_notifier_resume_handler(self, notification):
        self._idle_since = None

    def get_idle_time_seconds(self):
        if self._idle_since is None:
            return 0

        result = datetime.datetime.now() - self._idle_since
        return result.total_seconds()


