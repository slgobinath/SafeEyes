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

from collections import deque
import datetime
import logging
import pytest

from safeeyes import core
from safeeyes import model

import threading

from unittest import mock


class TestSafeEyesCore:
    @pytest.fixture(autouse=True)
    def set_time(self, time_machine):
        time_machine.move_to(
            datetime.datetime.fromisoformat("2024-08-25T13:00:00+00:00"), tick=False
        )

    @pytest.fixture(autouse=True)
    def monkeypatch_translations(self, monkeypatch):
        monkeypatch.setattr(
            core, "_", lambda message: "translated!: " + message, raising=False
        )
        monkeypatch.setattr(
            model, "_", lambda message: "translated!: " + message, raising=False
        )

    @pytest.fixture
    def sequential_threading(self, monkeypatch, time_machine):
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
        monkeypatch.setattr(
            core.utility,
            "execute_main_thread",
            lambda target_function, *args, **kwargs: target_function(*args, **kwargs),
        )

        handle = None

        def utility_start_thread(target_function, **kwargs):
            if not handle:
                raise Exception("handle must be initialized before first thread")
            handle.utility_start_thread(target_function, **kwargs)

        def time_sleep(time):
            if not handle:
                raise Exception("handle must be initialized before first sleep call")
            handle.sleep(time)

        monkeypatch.setattr(core.utility, "start_thread", utility_start_thread)

        monkeypatch.setattr(core.time, "sleep", time_sleep)

        class PatchedCondition(threading.Condition):
            def __init__(self, handle):
                super().__init__()
                self.handle = handle

            def wait(self, timeout):
                self.handle.wait_condvar(timeout)

        class Handle:
            thread = None
            task_queue = deque()
            running = True
            condvar_in = threading.Condition()
            condvar_out = threading.Condition()

            def __init__(self, safe_eyes_core):
                nonlocal handle
                nonlocal time_machine
                if handle:
                    raise Exception("only one handle is allowed per test call")
                handle = self
                self.time_machine = time_machine
                self.safe_eyes_core = safe_eyes_core
                self.safe_eyes_core.waiting_condition = PatchedCondition(self)

            def background_thread(self):
                while True:
                    with self.condvar_in:
                        success = self.condvar_in.wait(1)
                        if not success:
                            raise Exception("thread timed out")

                    if not self.running:
                        break

                    if self.task_queue:
                        (target_function, kwargs) = self.task_queue.popleft()
                        logging.debug(f"thread started {target_function}")
                        target_function(**kwargs)
                        logging.debug(f"thread finished {target_function}")

                    with self.condvar_out:
                        self.condvar_out.notify()

            def sleep(self, time):
                if self.thread is threading.current_thread():
                    with self.condvar_out:
                        self.condvar_out.notify()
                    self.time_machine.shift(delta=datetime.timedelta(seconds=time))
                    with self.condvar_in:
                        success = self.condvar_in.wait(1)
                        if not success:
                            raise Exception("thread timed out")

            def wait_condvar(self, time):
                if self.thread is not threading.current_thread():
                    raise Exception("waiting on condition may only happen in thread")

                with self.condvar_out:
                    self.condvar_out.notify()
                self.time_machine.shift(delta=datetime.timedelta(seconds=time))
                with self.condvar_in:
                    success = self.condvar_in.wait(1)
                    if not success:
                        raise Exception("thread timed out")

            def utility_start_thread(self, target_function, **kwargs):
                self.task_queue.append((target_function, kwargs))

                if self.thread is None:
                    self.thread = threading.Thread(
                        target=self.background_thread,
                        name="SequentialThreadingRunner",
                        daemon=False,
                        kwargs=kwargs,
                    )
                    self.thread.start()

            def next(self):
                assert self.thread

                with self.condvar_in:
                    self.condvar_in.notify()

                # wait until done:
                with self.condvar_out:
                    success = self.condvar_out.wait(1)
                    if not success:
                        raise Exception("thread timed out")

            def stop(self):
                self.running = False
                with self.condvar_in:
                    self.condvar_in.notify()

                if self.thread:
                    self.thread.join(1)

        yield Handle

        if handle:
            handle.stop()

    def test_create_empty(self):
        context = {}
        config = {
            "short_breaks": [],
            "long_breaks": [],
            "short_break_interval": 15,
            "long_break_interval": 75,
            "long_break_duration": 60,
            "short_break_duration": 15,
            "random_order": False,
            "postpone_duration": 5,
        }
        safe_eyes_core = core.SafeEyesCore(context)
        safe_eyes_core.initialize(config)

    def test_start_empty(self, sequential_threading):
        context = {}
        config = {
            "short_breaks": [],
            "long_breaks": [],
            "short_break_interval": 15,
            "long_break_interval": 75,
            "long_break_duration": 60,
            "short_break_duration": 15,
            "random_order": False,
            "postpone_duration": 5,
        }
        on_update_next_break = mock.Mock()
        safe_eyes_core = core.SafeEyesCore(context)
        safe_eyes_core.on_update_next_break += mock

        safe_eyes_core.initialize(config)

        safe_eyes_core.start()
        safe_eyes_core.stop()

        on_update_next_break.assert_not_called()

    def test_start(self, sequential_threading, time_machine):
        context = {
            "session": {},
        }
        config = {
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
        }
        on_update_next_break = mock.Mock()
        safe_eyes_core = core.SafeEyesCore(context)
        safe_eyes_core.on_update_next_break += on_update_next_break

        safe_eyes_core.initialize(config)

        sequential_threading_handle = sequential_threading(safe_eyes_core)

        safe_eyes_core.start()

        # start __scheduler_job
        sequential_threading_handle.next()

        assert context["state"] == model.State.WAITING

        on_update_next_break.assert_called_once()
        assert isinstance(on_update_next_break.call_args[0][0], model.Break)
        assert on_update_next_break.call_args[0][0].name == "translated!: break 1"
        on_update_next_break.reset_mock()

        # wait for end of __scheduler_job - we cannot stop while waiting on the condvar
        # this just moves us into waiting for __wait_until_prepare to start
        sequential_threading_handle.next()

        safe_eyes_core.stop()
        assert context["state"] == model.State.STOPPED

    def run_next_break(
        self,
        sequential_threading_handle,
        time_machine,
        safe_eyes_core,
        context,
        break_duration,
        break_name_translated,
    ):
        """Run one entire cycle of safe_eyes_core.

        It must be waiting for __scheduler_job to run. (This is the equivalent of
        State.WAITING).
        That means it must either be just started, or have finished the previous cycle.
        """
        on_update_next_break = mock.Mock()
        on_pre_break = mock.Mock(return_value=True)
        on_start_break = mock.Mock(return_value=True)
        start_break = mock.Mock()
        on_count_down = mock.Mock()

        safe_eyes_core.on_update_next_break += on_update_next_break
        safe_eyes_core.on_pre_break += on_pre_break
        safe_eyes_core.on_start_break += on_start_break
        safe_eyes_core.start_break += start_break
        safe_eyes_core.on_count_down += on_count_down

        # start __scheduler_job
        sequential_threading_handle.next()
        # wait until it reaches the condvar

        assert context["state"] == model.State.WAITING

        on_update_next_break.assert_called_once()
        assert isinstance(on_update_next_break.call_args[0][0], model.Break)
        assert on_update_next_break.call_args[0][0].name == break_name_translated
        on_update_next_break.reset_mock()

        # continue after condvar
        sequential_threading_handle.next()
        # end of __scheduler_job

        assert context["state"] == model.State.PRE_BREAK

        on_pre_break.assert_called_once()
        assert isinstance(on_pre_break.call_args[0][0], model.Break)
        assert on_pre_break.call_args[0][0].name == break_name_translated
        on_pre_break.reset_mock()

        # start __wait_until_prepare
        sequential_threading_handle.next()

        # wait until it reaches the condvar
        # continue after condvar
        sequential_threading_handle.next()
        # end of __wait_until_prepare

        # start __start_break
        sequential_threading_handle.next()

        # first sleep in __start_break
        sequential_threading_handle.next()

        on_start_break.assert_called_once()
        assert isinstance(on_start_break.call_args[0][0], model.Break)
        assert on_start_break.call_args[0][0].name == break_name_translated
        on_start_break.reset_mock()

        start_break.assert_called_once()
        assert isinstance(start_break.call_args[0][0], model.Break)
        assert start_break.call_args[0][0].name == break_name_translated
        start_break.reset_mock()

        assert context["state"] == model.State.BREAK

        # continue sleep in __start_break
        for i in range(break_duration - 2):
            sequential_threading_handle.next()

        sequential_threading_handle.next()
        # end of __start_break

        on_count_down.assert_called()
        assert on_count_down.call_count == break_duration
        on_count_down.reset_mock()

        assert context["state"] == model.State.BREAK

    def assert_datetime(self, string):
        if not string.endswith("+00:00"):
            string += "+00:00"
        assert datetime.datetime.now(
            datetime.timezone.utc
        ) == datetime.datetime.fromisoformat(string)

    def test_full_run_with_defaults(self, sequential_threading, time_machine):
        context = {
            "session": {},
        }
        short_break_duration = 15  # seconds
        short_break_interval = 15  # minutes
        pre_break_warning_time = 10  # seconds
        long_break_duration = 60  # seconds
        long_break_interval = 75  # minutes
        config = {
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
        }

        self.assert_datetime("2024-08-25T13:00:00")

        safe_eyes_core = core.SafeEyesCore(context)

        sequential_threading_handle = sequential_threading(safe_eyes_core)

        safe_eyes_core.initialize(config)

        safe_eyes_core.start()

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            context,
            short_break_duration,
            "translated!: break 1",
        )

        # Time passed: 15min 25s
        # 15min short_break_interval, 10 seconds pre_break_warning_time,
        # 15 seconds short_break_duration
        self.assert_datetime("2024-08-25T13:15:25")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            context,
            short_break_duration,
            "translated!: break 2",
        )

        self.assert_datetime("2024-08-25T13:30:50")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            context,
            short_break_duration,
            "translated!: break 3",
        )

        self.assert_datetime("2024-08-25T13:46:15")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            context,
            short_break_duration,
            "translated!: break 4",
        )

        self.assert_datetime("2024-08-25T14:01:40")

        self.run_next_break(
            sequential_threading_handle,
            time_machine,
            safe_eyes_core,
            context,
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
            context,
            short_break_duration,
            "translated!: break 1",
        )

        # Time passed: 15min 25s
        # 15min short_break_interval, 10 seconds pre_break_warning_time,
        # 15 seconds short_break_duration
        self.assert_datetime("2024-08-25T14:33:15")

        safe_eyes_core.stop()

        assert context["state"] == model.State.STOPPED
