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

from dataclasses import dataclass
import logging
import threading
import os
import select
import typing

from pywayland.client import Display
from pywayland.protocol.wayland.wl_seat import WlSeat


if typing.TYPE_CHECKING:
    from pywayland.protocol.ext_idle_notify_v1 import (
        ExtIdleNotifierV1,
        ExtIdleNotificationV1,
    )

from .interface import IdleMonitorInterface
from safeeyes import utility


@dataclass
class IdleConfig:
    on_idle: typing.Callable[[], None]
    on_resumed: typing.Callable[[], None]
    idle_time: float


class IdleMonitorExtIdleNotify(IdleMonitorInterface):
    _ext_idle_notify_internal: typing.Optional["ExtIdleNotifyInternal"] = None
    _thread: typing.Optional[threading.Thread] = None

    _r_channel_started: int
    _w_channel_started: int

    _r_channel_stop: int
    _w_channel_stop: int

    _r_channel_listen: int
    _w_channel_listen: int

    _idle_config: typing.Optional[IdleConfig] = None

    def init(self) -> None:
        try:
            from pywayland.protocol.ext_idle_notify_v1 import (
                ExtIdleNotifierV1,  # noqa: F401
                ExtIdleNotificationV1,  # noqa: F401
            )
        except Exception as e:
            logging.warning("The ext_idle_notify_v1 feature is not available.")
            logging.warning("This is likely due to an older version of Wayland.")
            raise e

        # we spawn one wayland client once
        # when the monitor is not running, it should be quite idle
        self._r_channel_started, self._w_channel_started = os.pipe()
        self._r_channel_stop, self._w_channel_stop = os.pipe()
        self._r_channel_listen, self._w_channel_listen = os.pipe()
        os.set_blocking(self._r_channel_listen, False)

        self._thread = threading.Thread(
            target=self._run, name="ExtIdleNotify", daemon=False
        )
        self._thread.start()

        result = os.read(self._r_channel_started, 1)

        if result == b"0":
            self._thread.join()
            self._thread = None
            raise Exception("ext-idle-notify-v1 not supported")

    def start_monitor(
        self,
        on_idle: typing.Callable[[], None],
        on_resumed: typing.Callable[[], None],
        idle_time: float,
    ) -> None:
        self._idle_config = IdleConfig(
            on_idle=on_idle,
            on_resumed=on_resumed,
            idle_time=idle_time,
        )

        # 1 means start listening, or that the configuration changed
        os.write(self._w_channel_listen, b"1")

    def configuration_changed(
        self,
        on_idle: typing.Callable[[], None],
        on_resumed: typing.Callable[[], None],
        idle_time: float,
    ) -> None:
        self._idle_config = IdleConfig(
            on_idle=on_idle,
            on_resumed=on_resumed,
            idle_time=idle_time,
        )

        # 1 means start listening, or that the configuration changed
        os.write(self._w_channel_listen, b"1")

    def is_monitor_running(self) -> bool:
        return self._idle_config is not None

    def _run(self) -> None:
        # Note that this creates a new connection to the wayland compositor.
        # This is not an issue per se, but does mean that the compositor sees this as
        # a new, separate client, that just happens to run in the same process as
        # the Safe Eyes gtk application.
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
                display,
                self._r_channel_stop,
                self._w_channel_started,
                self._r_channel_listen,
                self._on_idle,
                self._on_resumed,
                self._get_idle_time,
            )
            self._ext_idle_notify_internal.run()
            self._ext_idle_notify_internal = None

    def _on_idle(self) -> None:
        if self._idle_config is not None:
            self._idle_config.on_idle()

    def _on_resumed(self) -> None:
        if self._idle_config is not None:
            self._idle_config.on_resumed()

    def _get_idle_time(self) -> typing.Optional[float]:
        if self._idle_config is not None:
            return self._idle_config.idle_time
        else:
            return None

    def stop_monitor(self) -> None:
        # 0 means to stop listening
        # It's not an issue to write to the channel if we're not listening anymore
        # already
        os.write(self._w_channel_listen, b"0")

        self._idle_config = None

    def stop(self) -> None:
        # write anything, just to wake up the channel
        if self._thread is not None:
            os.write(self._w_channel_stop, b"!")
            self._thread.join()
            self._thread = None
            os.close(self._r_channel_stop)
            os.close(self._w_channel_stop)

            os.close(self._r_channel_started)
            os.close(self._w_channel_started)

            os.close(self._r_channel_listen)
            os.close(self._w_channel_listen)


class ExtIdleNotifyInternal:
    """This runs in the thread, and is only alive while the display exists.

    Split out into a separate object to simplify lifetime handling.
    """

    _idle_notifier: typing.Optional["ExtIdleNotifierV1"] = None
    _notification: typing.Optional["ExtIdleNotificationV1"] = None
    _display: Display
    _r_channel_stop: int
    _w_channel_started: int
    _r_channel_listen: int
    _seat: typing.Optional[WlSeat] = None

    _on_idle: typing.Callable[[], None]
    _on_resumed: typing.Callable[[], None]
    _get_idle_time: typing.Callable[[], typing.Optional[float]]

    def __init__(
        self,
        display: Display,
        r_channel_stop: int,
        w_channel_started: int,
        r_channel_listen: int,
        on_idle: typing.Callable[[], None],
        on_resumed: typing.Callable[[], None],
        get_idle_time: typing.Callable[[], typing.Optional[float]],
    ) -> None:
        self._display = display
        self._r_channel_stop = r_channel_stop
        self._w_channel_started = w_channel_started
        self._r_channel_listen = r_channel_listen
        self._on_idle = on_idle
        self._on_resumed = on_resumed
        self._get_idle_time = get_idle_time

    def run(self) -> None:
        """Run the wayland client.

        This will block until it's stopped by the channel.
        When this stops, self should no longer be used.
        """
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

        display_fd = self._display.get_fd()

        while True:
            self._display.flush()

            # this blocks until either there are new events in self._display
            # (retrieved using dispatch())
            # or until there are events in self._r_channel_stop - which means that
            # stop() was called
            # unfortunately, this seems like the best way to make sure that dispatch
            # doesn't block potentially forever (up to multiple seconds in my usage)
            read, _w, _x = select.select(
                (display_fd, self._r_channel_stop, self._r_channel_listen), (), ()
            )

            if self._r_channel_listen in read:
                # r_channel_listen is nonblocking
                # if there is nothing to read here, result should just be b""
                result = os.read(self._r_channel_listen, 1)
                if result == b"1":
                    self._listen()
                elif result == b"0":
                    if self._notification is not None:
                        self._notification.destroy()  # type: ignore[attr-defined]
                        self._notification = None

            if self._r_channel_stop in read:
                # the channel was written to, which means stop() was called
                break

            if display_fd in read:
                self._display.dispatch(block=True)

        self._display.roundtrip()

        if self._notification is not None:
            self._notification.destroy()  # type: ignore[attr-defined]
            self._notification = None

        self._display.roundtrip()

        self._seat = None
        self._idle_notifier = None

    def _listen(self):
        """Create a new idle notification listener.

        If one already exists, throw it away and recreate it with the new
        idle time.
        """
        # note that the typing doesn't work correctly here - it always says that
        # get_idle_notification is not defined
        # so just don't check this method
        if self._notification is not None:
            self._notification.destroy()
            self._notification = None

        timeout_sec = self._get_idle_time()
        if timeout_sec is None:
            logging.debug(
                "this should not happen. _listen() was called but idle time was not set"
            )
        self._notification = self._idle_notifier.get_idle_notification(
            int(timeout_sec * 1000), self._seat
        )
        self._notification.dispatcher["idled"] = self._idle_notifier_handler
        self._notification.dispatcher["resumed"] = self._idle_notifier_resume_handler

    def _global_handler(self, reg, id_num, iface_name, version) -> None:
        from pywayland.protocol.ext_idle_notify_v1 import ExtIdleNotifierV1

        if iface_name == "wl_seat":
            self._seat = reg.bind(id_num, WlSeat, version)
        if iface_name == "ext_idle_notifier_v1":
            self._idle_notifier = reg.bind(id_num, ExtIdleNotifierV1, version)

    def _idle_notifier_handler(self, notification) -> None:
        utility.execute_main_thread(self._on_idle)

    def _idle_notifier_resume_handler(self, notification) -> None:
        utility.execute_main_thread(self._on_resumed)
