#!/usr/bin/env python
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
"""Show health statistics on the break screen."""

import croniter
import datetime
import logging

context = None
session = None
statistics_reset_cron = None
default_statistics_reset_cron = "0 0 * * *"  # Every midnight
next_reset_time = None
start_time = None


def init(ctx, safeeyes_config, plugin_config):
    """Initialize the plugin."""
    global context
    global session
    global statistics_reset_cron

    logging.debug("Initialize Health Stats plugin")
    context = ctx
    statistics_reset_cron = plugin_config.get(
        "statistics_reset_cron", default_statistics_reset_cron
    )

    if session is None:
        # Read the session
        defaults = {
            "breaks": 0,
            "skipped_breaks": 0,
            "screen_time": 0,
            "total_breaks": 0,
            "total_skipped_breaks": 0,
            "total_screen_time": 0,
            "total_resets": 0,
        }

        session = context["session"]["plugin"].get("healthstats", {}).copy()
        session.update(defaults)
        if "no_of_breaks" in session:
            # Ignore old format session.
            session = defaults
        context["session"]["plugin"]["healthstats"] = session

    _get_next_reset_time()


def on_stop_break():
    # Check if break was skipped.
    global session
    if context["skipped"]:
        session["skipped_breaks"] += 1

    # Screen time is starting again.
    on_start()


def on_start_break(break_obj):
    global session
    session["breaks"] += 1

    # Screen time has stopped.
    on_stop()


def on_stop():
    global start_time
    _reset_stats()
    if start_time:
        screen_time = datetime.datetime.now() - start_time
        session["screen_time"] += round(screen_time.total_seconds())
        start_time = None


def get_widget_title(break_obj):
    """Return the widget title."""
    return _("Health Statistics")


def _reset_stats():
    global session

    # Check if the reset time has passed
    if next_reset_time and datetime.datetime.now() >= next_reset_time:
        logging.info("Resetting the health statistics")

        # Update the next_reset_time
        _get_next_reset_time()

        # Reset statistics
        session["total_breaks"] += session["breaks"]
        session["total_skipped_breaks"] += session["skipped_breaks"]
        session["total_screen_time"] += session["screen_time"]
        session["total_resets"] += 1
        session["breaks"] = 0
        session["skipped_breaks"] = 0
        session["screen_time"] = 0


def get_widget_content(break_obj):
    """Return the statistics."""
    global next_reset_time
    resets = session["total_resets"]
    if (
        session["screen_time"] > 21600
        or (session["breaks"] and session["skipped_breaks"] / session["breaks"]) >= 0.2
    ):
        # Unhealthy behavior -> Red broken heart
        heart = "💔️"
    else:
        # Healthy behavior -> Green heart
        heart = "💚"

    content = [
        heart,
        f"BREAKS: {session['breaks']}",
        f"SKIPPED: {session['skipped_breaks']}",
        f"SCREEN TIME: {_format_interval(session['screen_time'])}",
    ]

    if resets:
        content[1] += f" [{round(session['total_breaks'] / resets, 1)}]"
        content[2] += f" [{round(session['total_skipped_breaks'] / resets, 1)}]"
        content[3] += f" [{_format_interval(session['total_screen_time'] / resets)}]"

    content = "\t".join(content)
    if resets:
        content += f"\n\t[] = average of {resets} reset(s)"
    if next_reset_time is None:
        content += (
            f"\n\tSettings error in statistics reset interval: {statistics_reset_cron}"
        )
    return content


def on_start():
    """Track the start time."""
    global start_time
    _reset_stats()
    start_time = datetime.datetime.now()


def _get_next_reset_time():
    global next_reset_time
    global session

    try:
        cron = croniter.croniter(statistics_reset_cron, datetime.datetime.now())
        next_reset_time = cron.get_next(datetime.datetime)
        session["next_reset_time"] = next_reset_time.strftime("%Y-%m-%d %H:%M:%S")
        logging.debug("Health stats will be reset at " + session["next_reset_time"])
    except:  # noqa E722
        # TODO: consider catching Exception here instead of bare except
        logging.error("Error in statistics reset expression: " + statistics_reset_cron)
        next_reset_time = None


def _format_interval(seconds):
    screen_time = round(seconds / 60)
    hours, minutes = divmod(screen_time, 60)
    return "{:02d}:{:02d}".format(hours, minutes)
