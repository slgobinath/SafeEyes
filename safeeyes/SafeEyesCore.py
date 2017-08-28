# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2016  Gobinath

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


import time, datetime, threading, logging, sys
from safeeyes import Utility
from safeeyes.model import Break, BreakType


class SafeEyesCore:
	"""
	Core of Safe Eyes which runs the scheduler and notifies the breaks.
	"""

	def __init__(self, context, show_notification, start_break, end_break, on_countdown, update_next_break_info):
		"""
		Create an instance of SafeEyesCore and initialize the variables.
		"""
		self.next_break_index = 0;
		self.running = False
		self.show_notification = show_notification
		self.start_break = start_break
		self.end_break = end_break
		self.on_countdown = on_countdown
		self.update_next_break_info = update_next_break_info
		self.waiting_condition = threading.Condition()
		self.lock = threading.Lock()
		self.context = context
		self.context['skipped'] = False
		self.context['postponed'] = False

	def initialize(self, config, language):
		"""
		Initialize the internal properties from configuration
		"""
		logging.info("Initialize the core")
		self.breaks = []
		self.pre_break_warning_time = config['pre_break_warning_time']
		self.long_break_duration = config['long_break_duration']
		self.short_break_duration = config['short_break_duration']
		self.break_interval = config['break_interval']
		self.postpone_duration = config['postpone_duration']

		exercises = language['exercises'].copy()
		exercises.update(config['custom_exercises'])
		self.__init_breaks(BreakType.SHORT_BREAK, config['short_breaks'], exercises, config['no_of_short_breaks_per_long_break'])
		self.__init_breaks(BreakType.LONG_BREAK, config['long_breaks'], exercises, config['no_of_short_breaks_per_long_break'])
		self.break_count = len(self.breaks)

	def start(self):
		"""
		Start Safe Eyes is it is not running already.
		"""
		with self.lock:
			if not self.running:
				logging.info("Scheduling next break")
				self.running = True
				Utility.start_thread(self.__scheduler_job)

	def stop(self):
		"""
		Stop Safe Eyes if it is running.
		"""
		with self.lock:
			if not self.running:
				return

			logging.info("Stop the core")

			# Prevent resuming from a long break
			if self.__is_long_break():
				# Next break will be a long break.
				self.__select_next_break()
				pass

			# Stop the break thread
			self.waiting_condition.acquire()
			self.running = False
			self.waiting_condition.notify_all()
			self.waiting_condition.release()

	def skip(self):
		"""
		User skipped the break using Skip button
		"""
		self.context['skipped'] = True

	def postpone(self):
		"""
		User postponed the break using Postpone button
		"""
		self.context['postponed'] = True

	def __scheduler_job(self):
		"""
		Scheduler task to execute during every interval
		"""
		if not self.running:
			return

		time_to_wait = self.break_interval    # In minutes

		if self.context['postponed']:
			# Wait until the postpone time
			time_to_wait = self.postpone_duration
			self.context['postponed'] = False

		next_break_time = datetime.datetime.now() + datetime.timedelta(minutes=time_to_wait)
		self.update_next_break_info(next_break_time)

		if self.__is_long_break():
			self.context['break_type'] = 'long'
		else:
			self.context['break_type'] = 'short'

		# Wait for the pre break warning period
		logging.info("Waiting for {} minutes until next break".format(time_to_wait))
		self.__wait_for(time_to_wait * 60)    # Convert to seconds

		logging.info("Pre-break waiting is over")

		if not self.running:
			return

		self.__show_notification()

	def __show_notification(self):
		"""
		Show the notification and start the break after the notification.
		"""
		logging.info("Show the notification")
		# Show the notification
		self.show_notification()

		logging.info("Wait for {} seconds which is the time to prepare".format(self.pre_break_warning_time))
		# Wait for the pre break warning period
		self.__wait_for(self.pre_break_warning_time)
		self.__start_break()

	def __start_break(self):
		"""
		Start the break screen.
		"""
		# User can disable SafeEyes during notification
		if not self.running:
			return

		break_obj = self.breaks[self.next_break_index]
		seconds = break_obj.time
		self.context['break_length'] = seconds
		total_break_time = seconds

		# Show the break screen
		self.start_break(break_obj.name, break_obj.image)

		while seconds and self.running and not self.context['skipped'] and not self.context['postponed']:
			count_down = total_break_time - seconds
			self.context['count_down'] = count_down
			self.on_countdown(count_down, seconds)
			time.sleep(1)    # Sleep for 1 second
			seconds -= 1

		# Loop terminated because of timeout (not skipped) -> Close the break alert
		if not self.context['skipped'] and not self.context['postponed']:
			logging.info("Break is terminated automatically")
			self.end_break()

		# Reset the skipped flag
		self.context['skipped'] = False

		if not self.context['postponed']:
			self.__select_next_break()

		# Resume
		if self.running:
			# Schedule the break again
			Utility.start_thread(self.__scheduler_job)

	def __wait_for(self, duration):
		"""
		Wait until someone wake up or the timeout happens.
		"""
		self.waiting_condition.acquire()
		self.waiting_condition.wait(duration)
		self.waiting_condition.release()

	def __select_next_break(self):
		"""
		Select the next break.
		"""
		self.next_break_index = (self.next_break_index + 1) % self.break_count

	def __is_long_break(self):
		"""
		Check if the next break is long break.
		"""
		return self.breaks[self.next_break_index].type is BreakType.LONG_BREAK

	def __init_breaks(self, type, break_configs, exercises, no_of_short_breaks_per_long_break = 0):
		"""
		Fill the self.breaks using short and local breaks.
		"""
		# Defin the default break time
		default_break_time = self.short_break_duration

		# Duplicate short breaks to equally distribute the long breaks
		if type is BreakType.LONG_BREAK:
			default_break_time = self.long_break_duration
			required_short_breaks = no_of_short_breaks_per_long_break * len(break_configs)
			no_of_short_breaks = len(self.breaks)
			short_break_index = 0
			while no_of_short_breaks < required_short_breaks:
				self.breaks.append(self.breaks[short_break_index])
				short_break_index += 1
				no_of_short_breaks += 1
		
		iteration = 1
		for break_config in break_configs:
			exercise_name = break_config['name']
			name = None

			if exercise_name in exercises:
				name = exercises[exercise_name]
			else:
				logging.error('Exercise not found: ' + exercise_name)
				continue

			break_time = break_config.get('time', default_break_time)
			image = break_config.get('image')
			plugins = None # break_config.get('plugins', config['plugins'])

			# Validate time value
			if not isinstance(break_time, int) or break_time <= 0:
				logging.error('Invalid time in break: ' + str(break_config))
				continue

			break_obj = Break(type, name, break_time, image, plugins)
			if type is BreakType.SHORT_BREAK:
				self.breaks.append(break_obj)
			else:
				# Long break
				index = iteration * (no_of_short_breaks_per_long_break + 1) - 1
				self.breaks.insert(index, break_obj)
				iteration += 1
