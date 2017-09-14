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

import gi, logging
from safeeyes import Utility

"""
Safe Eyes audible alert plugin
"""

context = None

def init(ctx, safeeyes_config, plugin_config):
	"""
	Initialize the plugin.
	"""
	global context
	context = ctx


def on_stop_break():
	"""
	After the break, play the alert sound
	"""
	# Do not play if the break is skipped or postponed
	if context['skipped'] or context['postponed']:
		return

	logging.info('Playing audible alert')
	try:
		# Open the sound file
		path = Utility.get_resource_path('alert.wav')
		if path is None:
			return
		Utility.execute_command('aplay', [path])

	except Exception as e:
		logging.error('Unable to play audible alert')
