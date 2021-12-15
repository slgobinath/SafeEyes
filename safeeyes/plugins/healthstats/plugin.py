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
"""
Show health statistics on the break screen.
"""

import datetime
import logging
from typing import Optional, Tuple

import croniter
from croniter import CroniterBadCronError

from safeeyes.context import Context
from safeeyes.spi.breaks import Break
from safeeyes.spi.plugin import Widget, BreakAction
from safeeyes.util.locale import get_text as _


class HealthStats:

    def __init__(self, context: Context, config: dict):
        self.__context: Context = context
        self.__cron_expr: str = config.get('statistics_reset_cron', '0 0 * * *')
        # Compute the next reset time
        self.__safe_eyes_start_time = datetime.datetime.now()
        self.__next_reset_time: Optional[datetime.datetime] = self.__get_next_reset_time()
        self.enabled: bool = self.__next_reset_time is not None
        self.__session: dict = context.session.get_plugin('healthstats')

        if not self.enabled:
            # There is an error in the cron expression
            logging.error(
                "Health Stats: error in parsing the cron expression `%s`. Health Stats plugin is disabled." % self.__cron_expr)
            return

        if not self.__session:
            # Empty session
            self.__session['no_of_skipped_breaks'] = 0
            self.__session['no_of_breaks'] = 0
            self.__session['safe_eyes_start_time'] = self.__safe_eyes_start_time.strftime("%Y-%m-%d %H:%M:%S")
            self.__session['total_idle_time'] = 0
            self.__session['last_screen_time'] = -1
            self.__session[
                'next_reset_time'] = None if self.__next_reset_time is None else self.__next_reset_time.strftime(
                "%Y-%m-%d %H:%M:%S")
            context.session.set_plugin('healthstats', self.__session)
        else:
            last_start_time: str = self.__session.get('safe_eyes_start_time')
            last_reset_time = self.__session.get('next_reset_time')
            if last_start_time:
                self.__safe_eyes_start_time = datetime.datetime.strptime(last_start_time, "%Y-%m-%d %H:%M:%S")
            if last_reset_time:
                self.__next_reset_time = datetime.datetime.strptime(last_reset_time, "%Y-%m-%d %H:%M:%S")

        self.reset_stats()

    def reset_stats(self) -> int:
        # Check if the reset time has passed
        current_time = datetime.datetime.now()
        total_duration_sec = (current_time - self.__safe_eyes_start_time).total_seconds()
        if self.__next_reset_time is not None and current_time >= self.__next_reset_time:
            logging.debug("Health Stats: resetting the statistics")
            if self.__safe_eyes_start_time < self.__next_reset_time:
                # Safe Eyes is running even before the reset time
                # Consider the reset time as the new start time
                self.__safe_eyes_start_time = self.__next_reset_time
                total_duration_sec = (current_time - self.__safe_eyes_start_time).total_seconds()

            self.__session['no_of_breaks'] = 0
            self.__session['no_of_skipped_breaks'] = 0
            self.__session['safe_eyes_start_time'] = self.__safe_eyes_start_time.strftime("%Y-%m-%d %H:%M:%S")
            self.__session['total_idle_time'] = 0
            self.__session['last_screen_time'] = round(
                (total_duration_sec - self.__session.get('total_idle_time', 0)) / 60)

            # Update the next_reset_time
            self.__next_reset_time = self.__get_next_reset_time()
            if self.__next_reset_time is None:
                # This condition is added for a safety but not expected to run
                self.enabled = False
                self.__session['next_reset_time'] = None
            else:
                self.__session['next_reset_time'] = self.__next_reset_time.strftime("%Y-%m-%d %H:%M:%S")

        return int(total_duration_sec)

    def count_break(self) -> None:
        self.__session['no_of_breaks'] = self.__session.get('no_of_breaks', 0) + 1

    def count_skipped_break(self) -> None:
        self.__session['no_of_skipped_breaks'] = self.__session.get('no_of_skipped_breaks', 0) + 1

    def update_idle_time(self) -> int:
        self.__session['total_idle_time'] = self.get_total_idle_time() + self.__get_idle_time()
        return self.__session['total_idle_time']

    def get_total_idle_time(self) -> int:
        return self.__session.get('total_idle_time', 0)

    def get_stats(self) -> Tuple[int, int, int, int, int]:
        no_breaks = self.__session.get('no_of_breaks', 1)
        skipped_breaks = self.__session.get('no_of_skipped_breaks', 0)
        total_duration = self.reset_stats()
        screen_time = round((total_duration - self.get_total_idle_time()) / 60)
        last_screen_time = self.__session.get('last_screen_time', 0)
        return no_breaks, skipped_breaks, total_duration, screen_time, last_screen_time

    def __get_idle_time(self) -> int:
        """
        Get the system idle time from the Smart Pause plugin.
        """
        session_config = self.__context.session.get_plugin('smartpause')
        return session_config.get('idle_period', 0)

    def __get_next_reset_time(self) -> Optional[datetime.datetime]:
        try:
            cron = croniter.croniter(self.__cron_expr, datetime.datetime.now())
            next_time = cron.get_next(datetime.datetime)
            logging.debug("Health Stats: statistics will be reset at " + next_time.strftime("%Y-%m-%d %H:%M:%S"))
            return next_time
        except CroniterBadCronError:
            # Error in getting the next reset time
            return None


stats: HealthStats


def init(ctx: Context, plugin_config: dict) -> None:
    """
    Initialize the plugin.
    """
    global stats
    stats = HealthStats(ctx, plugin_config)


def on_start_break(break_obj: Break) -> None:
    if stats.enabled:
        stats.count_break()


def on_stop_break(break_obj: Break, break_action: BreakAction) -> None:
    """
    After the break, check if it is skipped.
    """
    if stats.enabled and break_action.skipped:
        stats.count_skipped_break()


def get_widget(break_obj: Break) -> Optional[Widget]:
    # Check if the plugin is enabled
    if not stats.enabled:
        return None

    no_breaks, skipped_breaks, total_duration, screen_time, last_screen_time = stats.get_stats()

    hours, minutes = divmod(screen_time, 60)
    time_format = '{:02d}:{:02d}'.format(hours, minutes)
    if hours > 6 or round((skipped_breaks / no_breaks), 1) >= 0.2:
        # Unhealthy behavior -> Red broken heart
        heart = '💔️'
    else:
        # Healthy behavior -> Green heart
        heart = '💚'
    if last_screen_time < 0:
        screen_time_diff = ''
    else:
        hrs_diff, mins_diff = divmod(abs(screen_time - last_screen_time), 60)
        symbol = ''
        if screen_time > last_screen_time:
            symbol = '+'
        elif screen_time < last_screen_time:
            symbol = '-'
        screen_time_diff = ' ( {}{:02d}:{:02d} )'.format(symbol, hrs_diff, mins_diff)
    content = "{}\tBREAKS: {}\tSKIPPED: {}\tSCREEN TIME: {}{}".format(heart, no_breaks, skipped_breaks,
                                                                      time_format, screen_time_diff)

    return Widget(_('Health Statistics'), content)


def on_start() -> None:
    """
    Add the idle period to the total idle time.
    """
    # Check if the plugin is enabled
    if stats.enabled:
        stats.reset_stats()
        stats.update_idle_time()
