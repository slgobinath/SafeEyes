#!/usr/bin/env python
# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2024 Leo (@undefiened), based on the code written by Gobinath

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
"""Limit how many breaks can be skipped or postponed in a row."""

import logging

context = None
no_of_skipped_breaks = 0
session = None
enabled = True


def init(ctx, safeeyes_config, plugin_config):
    """Initialize the plugin."""
    global enabled
    global context
    global session
    global no_of_skipped_breaks
    global no_allowed_skips

    logging.debug("Initialize Limit consecutive skipping plugin")
    context = ctx

    no_allowed_skips = plugin_config.get("number_of_allowed_skips_in_a_row", 2)

    if session is None:
        # Read the session
        session = context["session"]["plugin"].get("limitconsecutiveskipping", None)
        if session is None:
            session = {"no_of_skipped_breaks": 0}
            context["session"]["plugin"]["limitconsecutiveskipping"] = session
        no_of_skipped_breaks = session.get("no_of_skipped_breaks", 0)


def on_stop_break():
    """After the break, check if it is skipped."""
    # Check if the plugin is enabled
    if not enabled:
        return

    global no_of_skipped_breaks
    if context["skipped"] or context["postponed"]:
        no_of_skipped_breaks += 1
        session["no_of_skipped_breaks"] = no_of_skipped_breaks
    else:
        no_of_skipped_breaks = 0
        session["no_of_skipped_breaks"] = no_of_skipped_breaks


def on_start_break(break_obj):
    logging.debug(
        "Skipped / allowed = {} / {}".format(no_of_skipped_breaks, no_allowed_skips)
    )

    if no_of_skipped_breaks >= no_allowed_skips:
        context["postpone_button_disabled"] = True
        context["skip_button_disabled"] = True


def get_widget_title(break_obj):
    """Return the widget title."""
    # Check if the plugin is enabled
    if not enabled:
        return ""

    return _("Limit Consecutive Skipping")


def get_widget_content(break_obj):
    """Return the statistics."""
    # Check if the plugin is enabled
    if not enabled:
        return ""

    return _("Skipped or postponed %(num)d/%(allowed)d breaks in a row") % {
        "num": no_of_skipped_breaks,
        "allowed": no_allowed_skips,
    }
