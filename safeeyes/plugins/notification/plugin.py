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

import logging

import gi
from safeeyes.model import BreakType

gi.require_version('Notify', '0.7')
from gi.repository import Notify

"""
Safe Eyes Notification plugin
"""

APPINDICATOR_ID = 'safeeyes'
notification = None
context = None
warning_time = 10

Notify.init(APPINDICATOR_ID)


def init(ctx, safeeyes_config, plugin_config):
    """
    Initialize the plugin.
    """
    global context
    global warning_time
    logging.debug('Initialize Notification plugin')
    context = ctx
    warning_time = safeeyes_config.get('pre_break_warning_time')


def on_pre_break(break_obj):
    """
    Show the notification
    """
    # Construct the message based on the type of the next break
    global notification
    logging.info('Show the notification')
    message = '\n'
    if break_obj.type == BreakType.SHORT_BREAK:
        message += (_('Ready for a short break in %s seconds') % warning_time)
    else:
        message += (_('Ready for a long break in %s seconds') % warning_time)

    notification = Notify.Notification.new('Safe Eyes', message, icon='safeeyes_enabled')
    try:
        notification.show()
    except BaseException:
        logging.error('Failed to show the notification')


def on_start_break(break_obj):
    """
    Close the notification.
    """
    global notification
    logging.info('Close pre-break notification')
    if notification:
        try:
            notification.close()
            notification = None
        except BaseException:
            # Some operating systems automatically close the notification.
            pass


def on_exit():
    """
    Uninitialize the registered notificaion.
    """
    logging.debug('Stop Notification plugin')
    Notify.uninit()
