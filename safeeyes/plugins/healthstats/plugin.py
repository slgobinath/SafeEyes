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
reset_interval = 86400  # 24 hours in seconds


def init(ctx, safeeyes_config, plugin_config):
    """
    Initialize the plugin.
    """
    global context
    global session
    global no_of_skipped_breaks
    global no_of_breaks
    global no_of_cycles
    global reset_interval
    global safe_eyes_start_time
    global total_idle_time
    global last_screen_time
    logging.debug('Initialize Health Stats plugin')
    context = ctx
    reset_interval = plugin_config.get('statistics_reset_interval', 24) * 3600
    if session is None:
        session = context['session']['plugin'].get('healthstats', None)
        if session is None:
            session = {'no_of_skipped_breaks': 0,
                       'no_of_breaks': 0,
                       'no_of_cycles': -1,
                       'safe_eyes_start_time': safe_eyes_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                       'total_idle_time': 0,
                       'last_screen_time': -1}
            context['session']['plugin']['healthstats'] = session
        no_of_skipped_breaks = session.get('no_of_skipped_breaks', 0)
        no_of_breaks = session.get('no_of_breaks', 0)
        no_of_cycles = session.get('no_of_cycles', -1)
        total_idle_time = session.get('total_idle_time', 0)
        last_screen_time = session.get('last_screen_time', -1)
        str_time = session.get('safe_eyes_start_time', None)
        if str_time:
            safe_eyes_start_time = datetime.datetime.strptime(str_time, "%Y-%m-%d %H:%M:%S")
    _reset_stats()


def on_stop_break():
    """
    After the break, check if it is skipped.
    """
    global no_of_skipped_breaks
    if context['skipped']:
        no_of_skipped_breaks += 1
        session['no_of_skipped_breaks'] = no_of_skipped_breaks


def get_widget_title(break_obj):
    """
    Return the widget title.
    """
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
    current_time = datetime.datetime.now()
    total_duration_sec = (current_time - safe_eyes_start_time).total_seconds()
    if total_duration_sec >= reset_interval:
        total_duration_sec -= reset_interval
        safe_eyes_start_time = current_time - \
            datetime.timedelta(seconds=total_duration_sec)
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

    return total_duration_sec


def get_widget_content(break_obj):
    """
    Return the statistics.
    """
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
    _reset_stats()
    global total_idle_time
    # idle_period is provided by Smart Pause plugin
    total_idle_time += context.get('idle_period', 0)
    session['total_idle_time'] = total_idle_time
