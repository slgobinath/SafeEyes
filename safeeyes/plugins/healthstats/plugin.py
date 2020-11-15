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
"""
Show health statistics on the break screen.
"""

import croniter
import datetime
import logging

context = None
no_of_skipped_breaks = 0
no_of_breaks = 0
no_of_cycles = -1
session = None
safe_eyes_start_time = datetime.datetime.now()
total_idle_time = 0
last_screen_time = -1
statistics_reset_cron = '0 0 * * *'  # Every midnight
time_to_reset_break = datetime.datetime.now()
next_reset_time = None
enabled = True

def init(ctx, safeeyes_config, plugin_config):
    """
    Initialize the plugin.
    """
    global enabled
    global context
    global session
    global no_of_skipped_breaks
    global no_of_breaks
    global no_of_cycles
    global statistics_reset_cron
    global safe_eyes_start_time
    global total_idle_time
    global last_screen_time
    global next_reset_time

    logging.debug('Initialize Health Stats plugin')
    context = ctx
    statistics_reset_cron = plugin_config.get('statistics_reset_cron', '0 0 * * *')
    # Compute the next reset time
    next_reset_time = _get_next_reset_time(datetime.datetime.now(), statistics_reset_cron)
    enabled = next_reset_time is not None

    if not enabled:
        # There is an error in the cron expression
        logging.error("Error in parsing the cron expression `" + statistics_reset_cron + "`. Health Stats plugin is disabled.")
        return

    if session is None:
        # Read the session
        session = context['session']['plugin'].get('healthstats', None)
        if session is None:
            session = {'no_of_skipped_breaks': 0,
                       'no_of_breaks': 0,
                       'no_of_cycles': -1,
                       'safe_eyes_start_time': safe_eyes_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                       'total_idle_time': 0,
                       'last_screen_time': -1,
                       'next_reset_time': next_reset_time.strftime("%Y-%m-%d %H:%M:%S")}
            context['session']['plugin']['healthstats'] = session
        no_of_skipped_breaks = session.get('no_of_skipped_breaks', 0)
        no_of_breaks = session.get('no_of_breaks', 0)
        no_of_cycles = session.get('no_of_cycles', -1)
        total_idle_time = session.get('total_idle_time', 0)
        last_screen_time = session.get('last_screen_time', -1)
        str_time = session.get('safe_eyes_start_time', None)
        str_next_reset_time = session.get('next_reset_time', None)
        if str_time:
            safe_eyes_start_time = datetime.datetime.strptime(str_time, "%Y-%m-%d %H:%M:%S")
        if str_next_reset_time:
            next_reset_time = datetime.datetime.strptime(str_time, "%Y-%m-%d %H:%M:%S")
            
    _reset_stats()


def on_stop_break():
    """
    After the break, check if it is skipped.
    """
    # Check if the plugin is enabled
    if not enabled:
        return

    global no_of_skipped_breaks
    if context['skipped']:
        no_of_skipped_breaks += 1
        session['no_of_skipped_breaks'] = no_of_skipped_breaks


def get_widget_title(break_obj):
    """
    Return the widget title.
    """
    # Check if the plugin is enabled
    if not enabled:
        return ""

    global no_of_breaks
    global no_of_cycles
    no_of_breaks += 1
    if context['new_cycle']:
        no_of_cycles += 1
    session['no_of_breaks'] = no_of_breaks
    session['no_of_cycles'] = no_of_cycles
    session['safe_eyes_start_time'] = safe_eyes_start_time.strftime("%Y-%m-%d %H:%M:%S")
    session['total_idle_time'] = total_idle_time
    session['last_screen_time'] = last_screen_time
    return _('Health Statistics')


def _reset_stats():
    global no_of_breaks
    global no_of_cycles
    global safe_eyes_start_time
    global total_idle_time
    global no_of_skipped_breaks
    global last_screen_time
    global next_reset_time

    # Check if the reset time has passed
    current_time = datetime.datetime.now()
    total_duration_sec = (current_time - safe_eyes_start_time).total_seconds()
    if current_time >= next_reset_time:
        logging.debug("Resetting the health statistics")
        # Reset statistics
        if safe_eyes_start_time < next_reset_time:
            # Safe Eyes is running even before the reset time
            # Consider the reset time as the new start time
            safe_eyes_start_time = next_reset_time
            total_duration_sec = (current_time - safe_eyes_start_time).total_seconds()

        # Update the next_reset_time
        next_reset_time = _get_next_reset_time(current_time, statistics_reset_cron)

        last_screen_time = round((total_duration_sec - total_idle_time) / 60)
        total_idle_time = 0
        no_of_breaks = 0
        no_of_cycles = 0
        no_of_skipped_breaks = 0
        session['no_of_breaks'] = 0
        session['no_of_cycles'] = 0
        session['no_of_skipped_breaks'] = 0
        session['safe_eyes_start_time'] = safe_eyes_start_time.strftime("%Y-%m-%d %H:%M:%S")
        session['total_idle_time'] = total_idle_time
        session['last_screen_time'] = last_screen_time
        session['next_reset_time'] = next_reset_time.strftime("%Y-%m-%d %H:%M:%S")

    return total_duration_sec


def get_widget_content(break_obj):
    """
    Return the statistics.
    """
    # Check if the plugin is enabled
    if not enabled:
        return ""

    total_duration_sec = _reset_stats()
    screen_time = round((total_duration_sec - total_idle_time) / 60)
    hours, minutes = divmod(screen_time, 60)
    time_format = '{:02d}:{:02d}'.format(hours, minutes)
    if hours > 6 or round((no_of_skipped_breaks / no_of_breaks), 1) >= 0.2:
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
    return "{}\tBREAKS: {}\tSKIPPED: {}\tCYCLES: {}\tSCREEN TIME: {}{}".format(heart, no_of_breaks, no_of_skipped_breaks, no_of_cycles, time_format, screen_time_diff)


def on_start():
    """
    Add the idle period to the total idle time.
    """
    # Check if the plugin is enabled
    if not enabled:
        return ""

    _reset_stats()
    global total_idle_time
    # idle_period is provided by Smart Pause plugin
    total_idle_time += context.get('idle_period', 0)
    session['total_idle_time'] = total_idle_time

def _get_next_reset_time(current_time, statistics_reset_cron):
    try:
        cron = croniter.croniter(statistics_reset_cron, current_time)
        next_time = cron.get_next(datetime.datetime)
        logging.debug("Health stats will be reset at " + next_time.strftime("%Y-%m-%d %H:%M:%S"))
        return next_time
    except:
        # Error in getting the next reset time
        return None