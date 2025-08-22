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

import pytest
import random
import typing
from unittest import mock
from safeeyes import context, model


class TestBreak:
    def test_break_short(self) -> None:
        b = model.Break(
            break_type=model.BreakType.SHORT_BREAK,
            name="test break",
            time=15,
            duration=15,
            image=None,
            plugins={},
        )

        assert b.is_short_break()
        assert not b.is_long_break()

    def test_break_long(self) -> None:
        b = model.Break(
            break_type=model.BreakType.LONG_BREAK,
            name="long break",
            time=75,
            duration=60,
            image=None,
            plugins={},
        )

        assert not b.is_short_break()
        assert b.is_long_break()


class TestBreakQueue:
    def test_create_empty(self) -> None:
        config = model.Config(
            user_config={
                "short_breaks": [],
                "long_breaks": [],
                "short_break_interval": 15,
                "long_break_interval": 75,
                "long_break_duration": 60,
                "short_break_duration": 15,
                "random_order": False,
            },
            system_config={},
        )

        ctx = context.Context(
            api=mock.Mock(spec=context.API), locale="en_US", version="0.0.0", session={}
        )

        bq = model.BreakQueue.create(config, ctx)

        assert bq is None

    def get_bq_only_short(
        self, monkeypatch: pytest.MonkeyPatch, random_seed: typing.Optional[int] = None
    ) -> model.BreakQueue:
        if random_seed is not None:
            random.seed(random_seed)

        monkeypatch.setattr(
            model, "_", lambda message: "translated!: " + message, raising=False
        )

        config = model.Config(
            user_config={
                "short_breaks": [
                    {"name": "break 1"},
                    {"name": "break 2"},
                    {"name": "break 3"},
                ],
                "long_breaks": [],
                "short_break_interval": 15,
                "long_break_interval": 75,
                "long_break_duration": 60,
                "short_break_duration": 15,
                "random_order": random_seed is not None,
            },
            system_config={},
        )

        ctx = context.Context(
            api=mock.Mock(spec=context.API), locale="en_US", version="0.0.0", session={}
        )

        bq = model.BreakQueue.create(config, ctx)

        assert bq is not None

        return bq

    def get_bq_only_long(
        self, monkeypatch: pytest.MonkeyPatch, random_seed: typing.Optional[int] = None
    ) -> model.BreakQueue:
        if random_seed is not None:
            random.seed(random_seed)

        monkeypatch.setattr(
            model, "_", lambda message: "translated!: " + message, raising=False
        )

        config = model.Config(
            user_config={
                "short_breaks": [],
                "long_breaks": [
                    {"name": "long break 1"},
                    {"name": "long break 2"},
                    {"name": "long break 3"},
                ],
                "short_break_interval": 15,
                "long_break_interval": 75,
                "long_break_duration": 60,
                "short_break_duration": 15,
                "random_order": random_seed is not None,
            },
            system_config={},
        )

        ctx = context.Context(
            api=mock.Mock(spec=context.API), locale="en_US", version="0.0.0", session={}
        )

        bq = model.BreakQueue.create(config, ctx)

        assert bq is not None

        return bq

    def get_bq_full(
        self, monkeypatch: pytest.MonkeyPatch, random_seed: typing.Optional[int] = None
    ) -> model.BreakQueue:
        if random_seed is not None:
            random.seed(random_seed)

        monkeypatch.setattr(
            model, "_", lambda message: "translated!: " + message, raising=False
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
                "random_order": random_seed is not None,
            },
            system_config={},
        )

        ctx = context.Context(
            api=mock.Mock(spec=context.API), locale="en_US", version="0.0.0", session={}
        )

        bq = model.BreakQueue.create(config, ctx)

        assert bq is not None

        return bq

    def test_create_only_short(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bq = self.get_bq_only_short(monkeypatch)

        assert not bq.is_empty(model.BreakType.SHORT_BREAK)
        assert bq.is_empty(model.BreakType.LONG_BREAK)

    def test_only_short_repeat_get_break_no_change(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bq = self.get_bq_only_short(monkeypatch)

        next = bq.get_break()
        assert next.name == "translated!: break 1"

        next = bq.get_break()
        assert next.name == "translated!: break 1"

        assert not bq.is_long_break()

    def test_only_short_next_break(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bq = self.get_bq_only_short(monkeypatch)

        next = bq.get_break()
        assert next.name == "translated!: break 1"

        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 1"
        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 1"
        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"

    def test_only_short_next_break_random(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        random_seed = 5
        bq = self.get_bq_only_short(monkeypatch, random_seed)

        breaks = []
        breaks.append(bq.get_break().name)
        breaks.append(bq.next().name)
        breaks.append(bq.next().name)

        assert sorted(breaks) == [
            "translated!: break 1",
            "translated!: break 2",
            "translated!: break 3",
        ]

        prev_breaks = breaks

        for i in range(3):
            breaks = []
            breaks.append(bq.next().name)
            breaks.append(bq.next().name)
            breaks.append(bq.next().name)

            assert sorted(breaks) == [
                "translated!: break 1",
                "translated!: break 2",
                "translated!: break 3",
            ]

            assert prev_breaks != breaks
            prev_breaks = breaks

    def test_create_only_long(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bq = self.get_bq_only_long(monkeypatch)

        assert not bq.is_empty(model.BreakType.LONG_BREAK)
        assert bq.is_empty(model.BreakType.SHORT_BREAK)

    def test_only_long_repeat_get_break_no_change(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bq = self.get_bq_only_long(monkeypatch)

        next = bq.get_break()
        assert next.name == "translated!: long break 1"

        next = bq.get_break()
        assert next.name == "translated!: long break 1"

        assert bq.is_long_break()

    def test_only_long_next_break(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bq = self.get_bq_only_long(monkeypatch)

        next = bq.get_break()
        assert next.name == "translated!: long break 1"

        assert bq.next().name == "translated!: long break 2"
        assert bq.next().name == "translated!: long break 3"
        assert bq.next().name == "translated!: long break 1"
        assert bq.next().name == "translated!: long break 2"
        assert bq.next().name == "translated!: long break 3"
        assert bq.next().name == "translated!: long break 1"
        assert bq.next().name == "translated!: long break 2"
        assert bq.next().name == "translated!: long break 3"

    def test_only_long_next_break_random(self, monkeypatch: pytest.MonkeyPatch) -> None:
        random_seed = 5
        bq = self.get_bq_only_long(monkeypatch, random_seed)

        breaks = []
        breaks.append(bq.get_break().name)
        breaks.append(bq.next().name)
        breaks.append(bq.next().name)

        assert sorted(breaks) == [
            "translated!: long break 1",
            "translated!: long break 2",
            "translated!: long break 3",
        ]

        prev_breaks = breaks

        for i in range(3):
            breaks = []
            breaks.append(bq.next().name)
            breaks.append(bq.next().name)
            breaks.append(bq.next().name)

            assert sorted(breaks) == [
                "translated!: long break 1",
                "translated!: long break 2",
                "translated!: long break 3",
            ]

            assert prev_breaks != breaks
            prev_breaks = breaks

    def test_create_full(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bq = self.get_bq_full(monkeypatch)

        assert not bq.is_empty(model.BreakType.LONG_BREAK)
        assert not bq.is_empty(model.BreakType.SHORT_BREAK)

    def test_full_repeat_get_break_no_change(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bq = self.get_bq_full(monkeypatch)

        next = bq.get_break()
        assert next.name == "translated!: break 1"

        next = bq.get_break()
        assert next.name == "translated!: break 1"

        assert not bq.is_long_break()

    def test_full_next_break(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bq = self.get_bq_full(monkeypatch)

        next = bq.get_break()
        assert next.name == "translated!: break 1"
        assert not bq.is_long_break()

        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: long break 1"
        assert bq.is_long_break()
        assert bq.next().name == "translated!: break 1"
        assert not bq.is_long_break()
        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: long break 2"
        assert bq.next().name == "translated!: break 1"
        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: long break 3"
        assert bq.next().name == "translated!: break 1"
        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: long break 1"
        assert bq.next().name == "translated!: break 1"
        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: long break 2"
        assert bq.next().name == "translated!: break 1"
        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: long break 3"
        assert bq.next().name == "translated!: break 1"
        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: long break 1"

    def test_skip_long_break(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bq = self.get_bq_full(monkeypatch)

        next = bq.get_break()
        assert next.name == "translated!: break 1"
        assert not bq.is_long_break()

        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: long break 1"
        assert bq.is_long_break()
        assert bq.next().name == "translated!: break 1"
        assert not bq.is_long_break()
        assert bq.next().name == "translated!: break 2"

        bq.skip_long_break()

        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: break 1"
        assert bq.next().name == "translated!: long break 2"
        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: break 1"
        assert bq.next().name == "translated!: long break 3"

    def test_skip_long_break_before_long_break(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bq = self.get_bq_full(monkeypatch)

        next = bq.get_break()
        assert next.name == "translated!: break 1"
        assert not bq.is_long_break()

        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: long break 1"
        assert bq.is_long_break()
        assert bq.next().name == "translated!: break 1"
        assert not bq.is_long_break()
        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: long break 2"

        assert bq.get_break().name == "translated!: long break 2"

        bq.skip_long_break()

        assert bq.get_break().name == "translated!: break 1"

        assert bq.next().name == "translated!: break 2"
        assert bq.next().name == "translated!: break 3"
        assert bq.next().name == "translated!: break 4"
        assert bq.next().name == "translated!: long break 3"

    def test_full_next_break_random(self, monkeypatch: pytest.MonkeyPatch) -> None:
        random_seed = 5
        bq = self.get_bq_full(monkeypatch, random_seed)

        first = True

        prev_breaks: list[list[str]] = []
        prev_long_breaks: list[list[str]] = []

        for i in range(5):
            long_breaks = []
            for i in range(3):
                breaks = []
                if first:
                    first = False
                    breaks.append(bq.get_break().name)
                else:
                    breaks.append(bq.next().name)
                breaks.append(bq.next().name)
                breaks.append(bq.next().name)
                breaks.append(bq.next().name)
                long_breaks.append(bq.next().name)

                # assert that we used all breaks in this iteration
                assert sorted(breaks) == [
                    "translated!: break 1",
                    "translated!: break 2",
                    "translated!: break 3",
                    "translated!: break 4",
                ]

                # assert that not all the iterations are exactly the same order
                # (this may happen randomly sometimes of course - at least one
                # should be different)
                assert self.at_least_one_different(prev_breaks, breaks)
                prev_breaks.append(breaks)

            assert sorted(long_breaks) == [
                "translated!: long break 1",
                "translated!: long break 2",
                "translated!: long break 3",
            ]
            assert self.at_least_one_different(prev_long_breaks, long_breaks)
            prev_long_breaks.append(long_breaks)

    def at_least_one_different(
        self, previous: list[list[str]], current: list[str]
    ) -> bool:
        if len(previous) == 0:
            return True

        for prev in previous:
            if prev != current:
                return True

        return False
