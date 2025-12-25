# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2025  Mel Dafert <m@dafert.at>

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

import datetime
import pytest
import typing

from safeeyes import context
from safeeyes import core
from safeeyes import model

from time_machine import TimeMachineFixture

from unittest import mock


class SafeEyesCoreHandle:
    callback: typing.Optional[typing.Tuple[typing.Callable, int]] = None
    safe_eyes_core: core.SafeEyesCore
    time_machine: TimeMachineFixture

    def __init__(
        self,
        safe_eyes_core: core.SafeEyesCore,
        time_machine: TimeMachineFixture,
    ):
        self.time_machine = time_machine
        self.safe_eyes_core = safe_eyes_core

    def timeout_add_seconds(self, duration: int, callback: typing.Callable) -> int:
        if self.callback is not None:
            raise Exception("only one callback supported. need to make this smarter")
        self.callback = (callback, duration)
        return 1

    def source_remove(self, source_id: int) -> None:
        if self.callback is None:
            raise Exception("no callback registered")
        self.callback = None

    def next(self) -> None:
        assert self.callback

        (callback, duration) = self.callback
        self.callback = None
        self.time_machine.shift(delta=datetime.timedelta(seconds=duration))
        callback()


SequentialThreadingFixture: typing.TypeAlias = typing.Callable[
    [core.SafeEyesCore], SafeEyesCoreHandle
]


class TestSafeEyesCore:
    @pytest.fixture(autouse=True)
    def set_time(self, time_machine):
        time_machine.move_to(
            datetime.datetime.fromisoformat("2024-08-25T13:00:00+00:00"), tick=False
        )

    @pytest.fixture(autouse=True)
    def monkeypatch_translations(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            core, "_", lambda message: "translated!: " + message, raising=False
        )
        monkeypatch.setattr(
            model, "_", lambda message: "translated!: " + message, raising=False
        )

    @pytest.fixture
    def sequential_threading(
        self,
        monkeypatch: pytest.MonkeyPatch,
        time_machine: TimeMachineFixture,
    ) -> typing.Generator[SequentialThreadingFixture]:
        """This fixture allows stopping threads at any point.

        It is hard-coded for SafeEyesCore, the handle class returned by the fixture must
        be initialized with a SafeEyesCore instance to be patched.
        With this, all sleeping/blocking/thread starting calls inside SafeEyesCore are
        intercepted, and paused.
        Additionally, all threads inside SafeEyesCore run sequentially.
        The test code can use the next() method to unpause the thread,
        which will run until the next sleeping/blocking/thread starting call,
        after which it needs to be woken up using next() again.
        The next() method blocks the test code while the thread is running.
        """
        # executes instantly, on the same thread
        # no need to switch threads, as we don't use any gtk things
        handle: typing.Optional["SafeEyesCoreHandle"] = None

        def timeout_add_seconds(duration, callback) -> int:
            if not handle:
                raise Exception("handle must be initialized before first sleep call")
            return handle.timeout_add_seconds(duration, callback)

        def source_remove(source_id: int) -> None:
            if not handle:
                raise Exception("handle must be initialized before first call")
            handle.source_remove(source_id)

        monkeypatch.setattr(core.GLib, "timeout_add_seconds", timeout_add_seconds)
        monkeypatch.setattr(core.GLib, "source_remove", source_remove)

        def create_handle(safe_eyes_core: core.SafeEyesCore) -> SafeEyesCoreHandle:
            nonlocal time_machine
            nonlocal handle
            if handle:
                raise Exception("only one handle is allowed per test call")

            handle = SafeEyesCoreHandle(safe_eyes_core, time_machine)

            return handle

        yield create_handle

    def run_next_break(
        self,
        sequential_threading_handle: SafeEyesCoreHandle,
        time_machine: TimeMachineFixture,
        safe_eyes_core: core.SafeEyesCore,
        ctx: context.Context,
        break_duration: int,
        break_name_translated: str,
        initial: bool = False,
    ):
        """Run one entire cycle of safe_eyes_core.

        If initial is True, it must not be started yet.
        If initial is False, it must be in the state where __scheduler_job is about to
        be called again.
        This means it is in the BREAK state, but the break has ended and on_stop_break
        was already called.
        """
        on_update_next_break = mock.Mock()

        safe_eyes_core.on_update_next_break += on_update_next_break

        if initial:
            safe_eyes_core.start()
        else:
            assert ctx["state"] == model.State.BREAK

            sequential_threading_handle.next()

        assert ctx["state"] == model.State.WAITING

        on_update_next_break.assert_called_once()
        assert isinstance(on_update_next_break.call_args[0][0], model.Break)
        assert on_update_next_break.call_args[0][0].name == break_name_translated
        on_update_next_break.reset_mock()

        self.run_next_break_from_waiting_state(
            sequential_threading_handle,
            safe_eyes_core,
            ctx,
            break_duration,
            break_name_translated,
        )

    def run_next_break_from_waiting_state(
        self,
        sequential_threading_handle: SafeEyesCoreHandle,
        safe_eyes_core: core.SafeEyesCore,
        ctx: context.Context,
        break_duration: int,
        break_name_translated: str,
    ) -> None:
        on_pre_break = mock.Mock(return_value=True)
        on_start_break = mock.Mock(return_value=True)
        start_break = mock.Mock()
        on_count_down = mock.Mock()
        on_stop_break = mock.Mock()

        safe_eyes_core.on_pre_break += on_pre_break
        safe_eyes_core.on_start_break += on_start_break
        safe_eyes_core.start_break += start_break
        safe_eyes_core.on_count_down += on_count_down
        safe_eyes_core.on_stop_break += on_stop_break

        assert ctx["state"] == model.State.WAITING

        # continue after condvar
        sequential_threading_handle.next()
        # end of __scheduler_job

        assert ctx["state"] == model.State.PRE_BREAK

        on_pre_break.assert_called_once()
        assert isinstance(on_pre_break.call_args[0][0], model.Break)
        assert on_pre_break.call_args[0][0].name == break_name_translated
        on_pre_break.reset_mock()

        # start __wait_until_prepare
        # first sleep in __start_break
        sequential_threading_handle.next()

        assert ctx["state"] == model.State.BREAK

        on_start_break.assert_called_once()
        assert isinstance(on_start_break.call_args[0][0], model.Break)
        assert on_start_break.call_args[0][0].name == break_name_translated
        on_start_break.reset_mock()

        start_break.assert_called_once()
        assert isinstance(start_break.call_args[0][0], model.Break)
        assert start_break.call_args[0][0].name == break_name_translated
        start_break.reset_mock()

        assert ctx["state"] == model.State.BREAK

        # continue sleep in __start_break
        for i in range(break_duration - 1):
            sequential_threading_handle.next()

        assert ctx["state"] == model.State.BREAK

        sequential_threading_handle.next()
        # end of __start_break

        on_count_down.assert_called()
        assert on_count_down.call_count == break_duration
        on_count_down.reset_mock()

        on_stop_break.assert_called()
        assert on_stop_break.call_count == 1
        on_stop_break.reset_mock()

        assert ctx["state"] == model.State.BREAK

    def assert_datetime(self, string: str):
        if not string.endswith("+00:00"):
            string += "+00:00"
        assert datetime.datetime.now(
            datetime.timezone.utc
        ) == datetime.datetime.fromisoformat(string)

    def test_start_empty(self, sequential_threading: SequentialThreadingFixture):
        ctx = context.Context(
            api=mock.Mock(spec=context.API), locale="en_US", version="0.0.0", session={}
        )
        config = model.Config(
            user_config={
                "short_breaks": [],
                "long_breaks": [],
                "short_break_interval": 15,
                "long_break_interval": 75,
                "long_break_duration": 60,
                "short_break_duration": 15,
                "random_order": False,
                "postpone_duration": 5,
            },
            system_config={},
        )
        on_update_next_break = mock.Mock()
        safe_eyes_core = core.SafeEyesCore(ctx)
        safe_eyes_core.on_update_next_break += mock

        safe_eyes_core.initialize(config)

        safe_eyes_core.start()
        safe_eyes_core.stop()

        on_update_next_break.assert_not_called()

    def test_start(self, sequential_threading: SequentialThreadingFixture):
        ctx = context.Context(
            api=mock.Mock(spec=context.API), locale="en_US", version="0.0.0", session={}
        )
        config = model.Config(
            user_config={
                "short_breaks": [
                    {"name": "break 1"},
                    {"name": "break 2"},
                    {"name": "break 3"},
                    {"name": "break 4"},
                ],
                "long_breaks": [
                    {"name": "long break 1"},
                    {"name": "long break 2"},
                    {"name": "long break 3"},
                ],
                "short_break_interval": 15,
                "long_break_interval": 75,
                "long_break_duration": 60,
                "short_break_duration": 15,
                "random_order": False,
                "postpone_duration": 5,
                "pre_break_warning_time": 10,  # seconds
            },
            system_config={},
        )
        on_update_next_break = mock.Mock()
        safe_eyes_core = core.SafeEyesCore(ctx)
        safe_eyes_core.on_update_next_break += on_update_next_break

        safe_eyes_core.initialize(config)

        sequential_threading_handle = sequential_threading(safe_eyes_core)

        safe_eyes_core.start()

        assert ctx["state"] == model.State.WAITING

        on_update_next_break.assert_called_once()
        assert isinstance(on_update_next_break.call_args[0][0], model.Break)
        assert on_update_next_break.call_args[0][0].name == "translated!: break 1"
        on_update_next_break.reset_mock()

        # wait for end of __scheduler_job - we cannot stop while waiting on the condvar
        # this just moves us into waiting for __wait_until_prepare to start
        sequential_threading_handle.next()

        safe_eyes_core.stop()
        assert ctx["state"] == model.State.STOPPED

    def test_full_run_with_defaults(
        self,
        sequential_threading: SequentialThreadingFixture,
        time_machine: TimeMachineFixture,
    ):
        ctx = context.Context(
            api=mock.Mock(spec=context.API), locale="en_US", version="0.0.0", session={}
        )
        short_break_duration = 15  # seconds
        short_break_interval = 15  # minutes
        pre_break_warning_time = 10  # seconds
        long_break_duration = 60  # seconds
        long_break_interval = 75  # minutes
        config = model.Config(
            user_config={
                "short_breaks": [
                    {"name": "break 1"},
                    {"name": "break 2"},
                    {"name": "break 3"},
                    {"name": "break 4"},
                ],
                "long_breaks": [
                    {"name": "long break 1"},
                    {"name": "long break 2"},
                    {"name": "long break 3"},
                ],
                "short_break_interval": short_break_interval,
                "long_break_interval": long_break_interval,
                "long_break_duration": long_break_duration,
                "short_break_duration": short_break_duration,
                "pre_break_warning_time": pre_break_warning_time,
                "random_order": False,
                "postpone_duration": 5,
            },
            system_config={},
        )

        self.assert_datetime("2024-08-25T13:00:00")

        safe_eyes_core = core.SafeEyesCore(ctx)

        sequential_threading_handle = sequential_threading(safe_eyes_core)

        safe_eyes_core.initialize(config)

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 1",
            initial=True,
        )

        # Time passed: 15min 25s
        # 15min short_break_interval, 10 seconds pre_break_warning_time,
        # 15 seconds short_break_duration
        self.assert_datetime("2024-08-25T13:15:25")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 2",
        )

        self.assert_datetime("2024-08-25T13:30:50")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 3",
        )

        self.assert_datetime("2024-08-25T13:46:15")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 4",
        )

        self.assert_datetime("2024-08-25T14:01:40")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            long_break_duration,
            "translated!: long break 1",
        )

        # Time passed: 16min 10s
        # 15min short_break_interval (from previous, as long_break_interval must be
        # multiple)
        # 10 seconds pre_break_warning_time, 1 minute long_break_duration
        self.assert_datetime("2024-08-25T14:17:50")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 1",
        )

        # Time passed: 15min 25s
        # 15min short_break_interval, 10 seconds pre_break_warning_time,
        # 15 seconds short_break_duration
        self.assert_datetime("2024-08-25T14:33:15")

        safe_eyes_core.stop()

        assert ctx["state"] == model.State.STOPPED

    def test_long_duration_is_bigger_than_short_interval(
        self,
        sequential_threading: SequentialThreadingFixture,
        time_machine: TimeMachineFixture,
    ):
        """Example taken from https://github.com/slgobinath/safeeyes/issues/640."""
        ctx = context.Context(
            api=mock.Mock(spec=context.API), locale="en_US", version="0.0.0", session={}
        )
        short_break_duration = 300  # seconds = 5min
        short_break_interval = 25  # minutes
        pre_break_warning_time = 10  # seconds
        long_break_duration = 1800  # seconds = 30min
        long_break_interval = 100  # minutes
        config = model.Config(
            user_config={
                "short_breaks": [
                    {"name": "break 1"},
                    {"name": "break 2"},
                    {"name": "break 3"},
                    {"name": "break 4"},
                ],
                "long_breaks": [
                    {"name": "long break 1"},
                    {"name": "long break 2"},
                    {"name": "long break 3"},
                ],
                "short_break_interval": short_break_interval,
                "long_break_interval": long_break_interval,
                "long_break_duration": long_break_duration,
                "short_break_duration": short_break_duration,
                "pre_break_warning_time": pre_break_warning_time,
                "random_order": False,
                "postpone_duration": 5,
            },
            system_config={},
        )

        self.assert_datetime("2024-08-25T13:00:00")

        safe_eyes_core = core.SafeEyesCore(ctx)

        sequential_threading_handle = sequential_threading(safe_eyes_core)

        safe_eyes_core.initialize(config)

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 1",
            initial=True,
        )

        # Time passed: 30m 10s
        # 25min short_break_interval, 10 seconds pre_break_warning_time,
        # 5 minutes short_break_duration
        self.assert_datetime("2024-08-25T13:30:10")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 2",
        )

        self.assert_datetime("2024-08-25T14:00:20")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 3",
        )

        self.assert_datetime("2024-08-25T14:30:30")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            long_break_duration,
            "translated!: long break 1",
        )

        # Time passed: 55min 10s
        # 25min short_break_interval (from previous, as long_break_interval must be
        # multiple)
        # 10 seconds pre_break_warning_time, 30 minute long_break_duration
        self.assert_datetime("2024-08-25T15:25:40")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 4",
        )

        # Time passed: 30m 10s
        # 15min short_break_interval, 10 seconds pre_break_warning_time,
        # 15 seconds short_break_duration
        self.assert_datetime("2024-08-25T15:55:50")

        safe_eyes_core.stop()

        assert ctx["state"] == model.State.STOPPED

    def test_idle(
        self,
        sequential_threading: SequentialThreadingFixture,
        time_machine: TimeMachineFixture,
    ):
        """Test idling for short amount of time."""
        ctx = context.Context(
            api=mock.Mock(spec=context.API), locale="en_US", version="0.0.0", session={}
        )
        short_break_duration = 15  # seconds
        short_break_interval = 15  # minutes
        pre_break_warning_time = 10  # seconds
        long_break_duration = 60  # seconds
        long_break_interval = 75  # minutes
        config = model.Config(
            user_config={
                "short_breaks": [
                    {"name": "break 1"},
                    {"name": "break 2"},
                    {"name": "break 3"},
                    {"name": "break 4"},
                ],
                "long_breaks": [
                    {"name": "long break 1"},
                    {"name": "long break 2"},
                    {"name": "long break 3"},
                ],
                "short_break_interval": short_break_interval,
                "long_break_interval": long_break_interval,
                "long_break_duration": long_break_duration,
                "short_break_duration": short_break_duration,
                "pre_break_warning_time": pre_break_warning_time,
                "random_order": False,
                "postpone_duration": 5,
            },
            system_config={},
        )

        self.assert_datetime("2024-08-25T13:00:00")

        safe_eyes_core = core.SafeEyesCore(ctx)

        sequential_threading_handle = sequential_threading(safe_eyes_core)

        safe_eyes_core.initialize(config)

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 1",
            initial=True,
        )

        # Time passed: 15min 25s
        # 15min short_break_interval, 10 seconds pre_break_warning_time,
        # 15 seconds short_break_duration
        self.assert_datetime("2024-08-25T13:15:25")

        # idle, simulate behaviour of smartpause plugin
        idle_seconds = 30
        idle_period = datetime.timedelta(seconds=idle_seconds)

        safe_eyes_core.stop(is_resting=True)

        assert ctx["state"] == model.State.RESTING

        time_machine.shift(delta=idle_period)

        assert safe_eyes_core.scheduled_next_break_time is not None
        next_break = safe_eyes_core.scheduled_next_break_time + idle_period

        safe_eyes_core.start(next_break_time=next_break.timestamp())

        self.assert_datetime("2024-08-25T13:15:55")

        self.run_next_break_from_waiting_state(
            sequential_threading_handle,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 2",
        )

        self.assert_datetime("2024-08-25T13:31:20")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 3",
        )

        self.assert_datetime("2024-08-25T13:46:45")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 4",
        )

        self.assert_datetime("2024-08-25T14:02:10")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            long_break_duration,
            "translated!: long break 1",
        )

        # Time passed: 16min 10s
        # 15min short_break_interval (from previous, as long_break_interval must be
        # multiple)
        # 10 seconds pre_break_warning_time, 1 minute long_break_duration
        self.assert_datetime("2024-08-25T14:18:20")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 1",
        )

        # Time passed: 15min 25s
        # 15min short_break_interval, 10 seconds pre_break_warning_time,
        # 15 seconds short_break_duration
        self.assert_datetime("2024-08-25T14:33:45")

        safe_eyes_core.stop()

        assert ctx["state"] == model.State.STOPPED

    def test_idle_skip_long(
        self,
        sequential_threading: SequentialThreadingFixture,
        time_machine: TimeMachineFixture,
    ):
        """Test idling for longer than long break time."""
        ctx = context.Context(
            api=mock.Mock(spec=context.API), locale="en_US", version="0.0.0", session={}
        )
        short_break_duration = 15  # seconds
        short_break_interval = 15  # minutes
        pre_break_warning_time = 10  # seconds
        long_break_duration = 60  # seconds
        long_break_interval = 75  # minutes
        config = model.Config(
            user_config={
                "short_breaks": [
                    {"name": "break 1"},
                    {"name": "break 2"},
                    {"name": "break 3"},
                    {"name": "break 4"},
                ],
                "long_breaks": [
                    {"name": "long break 1"},
                    {"name": "long break 2"},
                    {"name": "long break 3"},
                ],
                "short_break_interval": short_break_interval,
                "long_break_interval": long_break_interval,
                "long_break_duration": long_break_duration,
                "short_break_duration": short_break_duration,
                "pre_break_warning_time": pre_break_warning_time,
                "random_order": False,
                "postpone_duration": 5,
            },
            system_config={},
        )

        self.assert_datetime("2024-08-25T13:00:00")

        safe_eyes_core = core.SafeEyesCore(ctx)

        sequential_threading_handle = sequential_threading(safe_eyes_core)

        safe_eyes_core.initialize(config)

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 1",
            initial=True,
        )

        # Time passed: 15min 25s
        # 15min short_break_interval, 10 seconds pre_break_warning_time,
        # 15 seconds short_break_duration
        self.assert_datetime("2024-08-25T13:15:25")

        # idle, simulate behaviour of smartpause plugin
        idle_seconds = 65
        idle_period = datetime.timedelta(seconds=idle_seconds)

        safe_eyes_core.stop(is_resting=True)

        assert ctx["state"] == model.State.RESTING

        time_machine.shift(delta=idle_period)

        assert safe_eyes_core.scheduled_next_break_time is not None
        next_break = safe_eyes_core.scheduled_next_break_time + idle_period

        safe_eyes_core.start(next_break_time=next_break.timestamp())

        self.assert_datetime("2024-08-25T13:16:30")

        self.run_next_break_from_waiting_state(
            sequential_threading_handle,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 2",
        )

        self.assert_datetime("2024-08-25T13:31:55")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 3",
        )

        self.assert_datetime("2024-08-25T13:47:20")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 4",
        )

        self.assert_datetime("2024-08-25T14:02:45")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 1",
        )

        self.assert_datetime("2024-08-25T14:18:10")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            long_break_duration,
            "translated!: long break 1",
        )

        # Time passed: 16min 10s
        # 15min short_break_interval (from previous, as long_break_interval must be
        # multiple)
        # 10 seconds pre_break_warning_time, 1 minute long_break_duration
        self.assert_datetime("2024-08-25T14:34:20")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 2",
        )

        # Time passed: 15min 25s
        # 15min short_break_interval, 10 seconds pre_break_warning_time,
        # 15 seconds short_break_duration
        self.assert_datetime("2024-08-25T14:49:45")

        safe_eyes_core.stop()

        assert ctx["state"] == model.State.STOPPED

    def test_idle_skip_long_before_long(
        self,
        sequential_threading: SequentialThreadingFixture,
        time_machine: TimeMachineFixture,
    ):
        """Test idling for longer than long break time, right before the next long
        break.

        This used to skip all the short breaks too.
        """
        ctx = context.Context(
            api=mock.Mock(spec=context.API), locale="en_US", version="0.0.0", session={}
        )
        short_break_duration = 15  # seconds
        short_break_interval = 15  # minutes
        pre_break_warning_time = 10  # seconds
        long_break_duration = 60  # seconds
        long_break_interval = 75  # minutes
        config = model.Config(
            user_config={
                "short_breaks": [
                    {"name": "break 1"},
                    {"name": "break 2"},
                    {"name": "break 3"},
                    {"name": "break 4"},
                ],
                "long_breaks": [
                    {"name": "long break 1"},
                    {"name": "long break 2"},
                    {"name": "long break 3"},
                ],
                "short_break_interval": short_break_interval,
                "long_break_interval": long_break_interval,
                "long_break_duration": long_break_duration,
                "short_break_duration": short_break_duration,
                "pre_break_warning_time": pre_break_warning_time,
                "random_order": False,
                "postpone_duration": 5,
            },
            system_config={},
        )

        self.assert_datetime("2024-08-25T13:00:00")

        safe_eyes_core = core.SafeEyesCore(ctx)

        sequential_threading_handle = sequential_threading(safe_eyes_core)

        safe_eyes_core.initialize(config)

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 1",
            initial=True,
        )

        # Time passed: 15min 25s
        # 15min short_break_interval, 10 seconds pre_break_warning_time,
        # 15 seconds short_break_duration
        self.assert_datetime("2024-08-25T13:15:25")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 2",
        )

        self.assert_datetime("2024-08-25T13:30:50")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 3",
        )

        self.assert_datetime("2024-08-25T13:46:15")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 4",
        )

        self.assert_datetime("2024-08-25T14:01:40")

        # idle, simulate behaviour of smartpause plugin
        idle_seconds = 65
        idle_period = datetime.timedelta(seconds=idle_seconds)

        safe_eyes_core.stop(is_resting=True)

        assert ctx["state"] == model.State.RESTING

        time_machine.shift(delta=idle_period)

        assert safe_eyes_core.scheduled_next_break_time is not None
        next_break = safe_eyes_core.scheduled_next_break_time + idle_period

        safe_eyes_core.start(next_break_time=next_break.timestamp())

        self.assert_datetime("2024-08-25T14:02:45")

        self.run_next_break_from_waiting_state(
            sequential_threading_handle,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 1",
        )

        self.assert_datetime("2024-08-25T14:18:10")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 2",
        )

        self.assert_datetime("2024-08-25T14:33:35")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 3",
        )

        self.assert_datetime("2024-08-25T14:49:00")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            short_break_duration,
            "translated!: break 4",
        )

        self.assert_datetime("2024-08-25T15:04:25")

        # note that long break 1 was skipped, and we went directly to long break 2
        # there's a note in BreakQueue.skip_long_break, we could fix it if needed, but
        # it seems too much effort to be worth it right now
        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            ctx,
            long_break_duration,
            "translated!: long break 2",
        )

        self.assert_datetime("2024-08-25T15:20:35")

        safe_eyes_core.stop()

        assert ctx["state"] == model.State.STOPPED
