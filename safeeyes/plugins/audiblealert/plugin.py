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

import gi, logging, pyaudio, wave
gi.require_version('Notify', '0.7')
from gi.repository import Notify
from safeeyes import Utility
from safeeyes.model import BreakType

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
	CHUNK = 1024
	try:
		# Open the sound file
		path = Utility.get_resource_path('alert.wav')
		if path is None:
			return
		sound = wave.open(path, 'rb')

		# Create a sound stream
		wrapper = pyaudio.PyAudio()
		stream = wrapper.open(format=wrapper.get_format_from_width(
			sound.getsampwidth()),
			channels=sound.getnchannels(),
			rate=sound.getframerate(),
			output=True)

		# Write file data into the sound stream
		data = sound.readframes(CHUNK)
		while data != b'':
			stream.write(data)
			data = sound.readframes(CHUNK)

		# Close steam
		stream.stop_stream()
		stream.close()
		sound.close()
		wrapper.terminate()

	except Exception as e:
		logging.warning('Unable to play audible alert')
		logging.exception(e)
