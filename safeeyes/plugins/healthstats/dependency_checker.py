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

import datetime
from safeeyes import utility

def _get_next_reset_time(current_time, statistics_reset_cron):
    import croniter
    try:
        cron = croniter.croniter(statistics_reset_cron, current_time)
        return cron.get_next(datetime.datetime)
    except:
        # Error in getting the next reset time
        return None

def validate(plugin_config, plugin_settings):
    if not utility.module_exist("croniter"):
        return _("Please install the Python module '%s'") % "croniter"

    # Validate the cron expression
    statistics_reset_cron = plugin_settings.get('statistics_reset_cron', '0 0 * * *')
    if _get_next_reset_time(datetime.datetime.now(), statistics_reset_cron) is None:
        return _("Invalid cron expression '%s'") % statistics_reset_cron
    else:
        return None
