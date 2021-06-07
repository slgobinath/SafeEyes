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

from safeeyes.context import Context
from safeeyes.env import system


def __is_valid_cron(expr: str) -> bool:
    from croniter import croniter
    from croniter.croniter import CroniterBadCronError
    try:
        return bool(croniter.expand(expr))
    except CroniterBadCronError:
        # Error in getting the next reset time
        return False


def validate(ctx: Context, plugin_config: dict, plugin_settings: dict):
    if not system.module_exists("croniter"):
        return _("Please install the Python module 'croniter'")

    # Validate the cron expression
    statistics_reset_cron = plugin_settings.get('statistics_reset_cron', '0 0 * * *')
    if __is_valid_cron(statistics_reset_cron) is None:
        return _("Invalid cron expression '%s'") % statistics_reset_cron
    else:
        return None
