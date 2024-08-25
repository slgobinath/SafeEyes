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
from time import sleep

from unittest import mock


class TestSafeEyesCore:
    @pytest.fixture(autouse=True)
    def set_time(self, time_machine):
        time_machine.move_to(datetime.datetime.fromisoformat("2024-08-25T13:00"))

    @pytest.fixture(autouse=True)
    def monkeypatch_translations(self, monkeypatch):
        monkeypatch.setattr(
            core, "_", lambda message: "translated!: " + message, raising=False
        )
        monkeypatch.setattr(
            model, "_", lambda message: "translated!: " + message, raising=False
        )

    @pytest.fixture
    def sequential_threading(self, monkeypatch):
        # executes instantly
        # TODO: separate thread?
        monkeypatch.setattr(
            core.utility,
            "execute_main_thread",
            lambda target_function, *args, **kwargs: target_function(*args, **kwargs),
        )

        class Handle:
            thread = None
            task_queue = deque()
            running = True
            condvar_in = threading.Condition()
            condvar_out = threading.Condition()

            def background_thread(self):
                while True:
                    with self.condvar_in:
                        success = self.condvar_in.wait(1)
                        if not success:
                            raise Exception("thread timed out")

                    if not self.running:
                        logging.debug("background task shutdown")
                        break

                    logging.debug("background task woken up")

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
                    with self.condvar_in:
                        success = self.condvar_in.wait(1)
                        if not success:
                            raise Exception("thread timed out")

            def utility_start_thread(self, target_function, **kwargs):
                self.task_queue.append((target_function, kwargs))

                if self.thread is None:
                    self.thread = threading.Thread(
                        target=self.background_thread,
                        name="WorkThread",
                        daemon=False,
                        kwargs=kwargs,
                    )
                    self.thread.start()

            def next(self):
                assert self.thread

                with self.condvar_in:
                    self.condvar_in.notify()

            def wait(self):
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

        handle = Handle()

        monkeypatch.setattr(core.utility, "start_thread", handle.utility_start_thread)

        monkeypatch.setattr(core.time, "sleep", lambda time: handle.sleep(time))

        yield handle

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

        safe_eyes_core.start()

        # start __scheduler_job
        sequential_threading.next()
        # FIXME: sleep is needed so code reaches the Condition
        sleep(0.1)
        assert context["state"] == model.State.WAITING

        on_update_next_break.assert_called_once()
        assert isinstance(on_update_next_break.call_args[0][0], model.Break)
        assert on_update_next_break.call_args[0][0].name == "translated!: break 1"
        on_update_next_break.reset_mock()

        with safe_eyes_core.lock:
            time_machine.shift(delta=datetime.timedelta(minutes=15))

            with safe_eyes_core.waiting_condition:
                logging.debug("notify")
                safe_eyes_core.waiting_condition.notify_all()

        logging.debug("wait for end of __scheduler_job")
        sequential_threading.wait()
        logging.debug("done waiting for end of __scheduler_job")

        safe_eyes_core.stop()
        assert context["state"] == model.State.STOPPED

        logging.debug("done")

    def test_actual(self, sequential_threading, time_machine):
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
            "pre_break_warning_time": 10,
            "random_order": False,
            "postpone_duration": 5,
        }
        on_update_next_break = mock.Mock()
        on_pre_break = mock.Mock(return_value=True)
        on_start_break = mock.Mock(return_value=True)
        start_break = mock.Mock()
        on_count_down = mock.Mock()
        safe_eyes_core = core.SafeEyesCore(context)
        safe_eyes_core.on_update_next_break += on_update_next_break
        safe_eyes_core.on_pre_break += on_pre_break
        safe_eyes_core.on_start_break += on_start_break
        safe_eyes_core.start_break += start_break
        safe_eyes_core.on_count_down += on_count_down

        safe_eyes_core.initialize(config)

        safe_eyes_core.start()

        # start __scheduler_job
        sequential_threading.next()
        # FIXME: sleep is needed so code reaches the Condition
        sleep(0.1)
        assert context["state"] == model.State.WAITING

        on_update_next_break.assert_called_once()
        assert isinstance(on_update_next_break.call_args[0][0], model.Break)
        assert on_update_next_break.call_args[0][0].name == "translated!: break 1"
        on_update_next_break.reset_mock()

        with safe_eyes_core.lock:
            time_machine.shift(delta=datetime.timedelta(minutes=15))

            with safe_eyes_core.waiting_condition:
                logging.debug("notify")
                safe_eyes_core.waiting_condition.notify_all()

        logging.debug("wait for end of __scheduler_job")
        sequential_threading.wait()
        logging.debug("done waiting for end of __scheduler_job")

        assert context["state"] == model.State.PRE_BREAK

        on_pre_break.assert_called_once()
        assert isinstance(on_pre_break.call_args[0][0], model.Break)
        assert on_pre_break.call_args[0][0].name == "translated!: break 1"
        on_pre_break.reset_mock()

        # start __wait_until_prepare
        sequential_threading.next()

        # FIXME: sleep is needed so code reaches the Condition
        sleep(0.1)
        with safe_eyes_core.lock:
            time_machine.shift(delta=datetime.timedelta(seconds=10))

            with safe_eyes_core.waiting_condition:
                logging.debug("notify")
                safe_eyes_core.waiting_condition.notify_all()

        logging.debug("wait for end of __wait_until_prepare")
        sequential_threading.wait()
        logging.debug("done waiting for end of __wait_until_prepare")

        # start __start_break
        sequential_threading.next()
        sequential_threading.wait()

        # first sleep in __start_break
        sequential_threading.next()

        on_start_break.assert_called_once()
        assert isinstance(on_start_break.call_args[0][0], model.Break)
        assert on_start_break.call_args[0][0].name == "translated!: break 1"
        on_start_break.reset_mock()

        start_break.assert_called_once()
        assert isinstance(start_break.call_args[0][0], model.Break)
        assert start_break.call_args[0][0].name == "translated!: break 1"
        start_break.reset_mock()

        assert context["state"] == model.State.BREAK

        # continue sleep in __start_break
        for i in range(config["short_break_duration"] - 1):
            sequential_threading.wait()
            sequential_threading.next()

        logging.debug("wait for end of __start_break")
        sequential_threading.wait()
        logging.debug("done waiting for end of __start_break")

        on_count_down.assert_called()
        assert on_count_down.call_count == 15
        on_count_down.reset_mock()

        assert context["state"] == model.State.BREAK

        safe_eyes_core.stop()

        on_update_next_break.assert_not_called()
        on_pre_break.assert_not_called()
        on_start_break.assert_not_called()
        start_break.assert_not_called()
        assert context["state"] == model.State.STOPPED
