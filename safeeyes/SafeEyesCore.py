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


import time, datetime, threading, logging
from safeeyes import Utility


class SafeEyesCore:
	"""
	Core of Safe Eyes which runs the scheduler and notifies the breaks.
	"""

	def __init__(self, context, show_notification, start_break, end_break, on_countdown, update_next_break_info):
		# Initialize the variables
		self.break_count = -1
		self.long_break_message_index = -1
		self.short_break_message_index = -1
		self.active = False
		self.running = False
		self.show_notification = show_notification
		self.start_break = start_break
		self.end_break = end_break
		self.on_countdown = on_countdown
		self.update_next_break_info = update_next_break_info
		self.notification_condition = threading.Condition()
		self.idle_condition = threading.Condition()
		self.lock = threading.Lock()
		self.context = context
		self.context['skipped'] = False
		self.context['postponed'] = False

	def initialize(self, config, language):
		"""
		Initialize the internal properties from configuration
		"""
		logging.info("Initialize the core")
		self.short_break_exercises = []    # language['exercises']['short_break_exercises']
		self.long_break_exercises = []     # language['exercises']['long_break_exercises']

		self.no_of_short_breaks_per_long_break = config['no_of_short_breaks_per_long_break']
		self.pre_break_warning_time = config['pre_break_warning_time']
		self.long_break_duration = config['long_break_duration']
		self.short_break_duration = config['short_break_duration']
		self.break_interval = config['break_interval']
		self.idle_time = config['idle_time']
		self.postpone_duration = config['postpone_duration']
		self.skip_break_window_classes = [x.lower() for x in config['active_window_class']['skip_break']]
		self.take_break_window_classes = [x.lower() for x in config['active_window_class']['take_break']]
		self.custom_exercises = config['custom_exercises']
		# Enable idle time pause only if xprintidle is available
		self.context['idle_pause_enabled'] = Utility.command_exist('xprintidle')

		exercises = language['exercises']
		for short_break_config in config['short_breaks']:
			exercise_name = short_break_config['name']
			name = None

			if exercise_name in self.custom_exercises:
				name = self.custom_exercises[exercise_name]
			else:
				name = exercises[exercise_name]

			break_time = short_break_config.get('time', self.short_break_duration)
			audible_alert = short_break_config.get('audible_alert', config['audible_alert'])
			image = short_break_config.get('image')

			# Validate time value
			if not isinstance(break_time, int) or break_time <= 0:
				logging.error('Invalid time in short break: ' + str(short_break_config))
				continue

			self.short_break_exercises.append([name, break_time, audible_alert, image])

		for long_break_config in config['long_breaks']:
			exercise_name = long_break_config['name']
			name = None

			if exercise_name in self.custom_exercises:
				name = self.custom_exercises[exercise_name]
			else:
				name = exercises[exercise_name]

			break_time = long_break_config.get('time', self.long_break_duration)
			audible_alert = long_break_config.get('audible_alert', config['audible_alert'])
			image = long_break_config.get('image')

			# Validate time value
			if not isinstance(break_time, int) or break_time <= 0:
				logging.error('Invalid time in long break: ' + str(long_break_config))
				continue

			self.long_break_exercises.append([name, break_time, audible_alert, image])

	def start(self):
		"""
		Start Safe Eyes is it is not running already.
		"""
		with self.lock:
			if not self.active:
				logging.info("Scheduling next break")
				self.active = True
				self.running = True
				Utility.start_thread(self.__scheduler_job)
				if self.context['idle_pause_enabled']:
					Utility.start_thread(self.__start_idle_monitor)

	def stop(self):
		"""
		Stop Safe Eyes if it is running.
		"""
		with self.lock:
			if self.active:
				logging.info("Stop the core")

				# Prevent resuming from a long break
				current_break_count = self.break_count = 0
				self.break_count = ((self.break_count + 1) % self.no_of_short_breaks_per_long_break)
				if self.__is_long_break():
					# Next break will be a long break. Leave the increment so that next break will be short break after the long
					pass
				else:
					# Reset to the current state
					self.break_count = current_break_count

				# Stop the break thread
				self.notification_condition.acquire()
				self.active = False
				self.running = False
				self.notification_condition.notify_all()
				self.notification_condition.release()

				# Stop the idle monitor
				self.idle_condition.acquire()
				self.idle_condition.notify_all()
				self.idle_condition.release()

	def pause(self):
		"""
		Pause Safe Eyes if it is running.
		"""
		with self.lock:
			if self.active and self.running:
				self.notification_condition.acquire()
				self.running = False
				self.notification_condition.notify_all()
				self.notification_condition.release()

	def resume(self):
		"""
		Resume Safe Eyes if it is not running.
		"""
		with self.lock:
			if self.active and not self.running:
				self.running = True
				Utility.start_thread(self.__scheduler_job)

	def skip_break(self):
		"""
		User skipped the break using Skip button
		"""
		self.context['skipped'] = True

	def postpone_break(self):
		"""
		User postponed the break using Postpone button
		"""
		self.context['postponed'] = True

	def __scheduler_job(self):
		"""
		Scheduler task to execute during every interval
		"""
		if not self.__is_running():
			return

		time_to_wait = self.break_interval    # In minutes

		if self.context['postponed']:
			# Reduce the break count by 1 to show the same break again
			if self.break_count == 0:
				self.break_count = -1
			else:
				self.break_count = ((self.break_count - 1) % self.no_of_short_breaks_per_long_break)
			if self.__is_long_break():
				self.long_break_message_index = (self.long_break_message_index - 1) % len(self.long_break_exercises)
			else:
				self.short_break_message_index = (self.short_break_message_index - 1) % len(self.short_break_exercises)

			# Wait until the postpone time
			time_to_wait = self.postpone_duration
			self.context['postponed'] = False

		next_break_time = datetime.datetime.now() + datetime.timedelta(minutes=time_to_wait)
		self.update_next_break_info(next_break_time)

		self.break_count = ((self.break_count + 1) % self.no_of_short_breaks_per_long_break)
		if self.__is_long_break():
			self.context['break_type'] = 'long'
		else:
			self.context['break_type'] = 'short'

		# Wait for the pre break warning period
		logging.info("Pre-break waiting for {} minutes".format(time_to_wait))
		self.notification_condition.acquire()
		self.notification_condition.wait(time_to_wait * 60)    # Convert to seconds
		self.notification_condition.release()

		logging.info("Pre-break waiting is over")

		if not self.__is_running():
			return

		logging.info("Ready to show the break")

		self.is_before_break = False
		Utility.execute_main_thread(self.__check_active_window)

	def __show_notification(self):
		"""
		Show the notification and start the break after the notification.
		"""
		# Show the notification
		self.show_notification()

		logging.info("Wait for {} seconds which is the time to prepare".format(self.pre_break_warning_time))
		# Wait for the pre break warning period
		self.notification_condition.acquire()
		self.notification_condition.wait(self.pre_break_warning_time)
		self.notification_condition.release()

		self.is_before_break = True
		Utility.execute_main_thread(self.__check_active_window)

	def __check_active_window(self):
		"""
		Check the active window for full-screen and user defined exceptions.
		"""
		# Check the active window again. (User might changed the window)
		if self.__is_running() and Utility.is_active_window_skipped(self.skip_break_window_classes, self.take_break_window_classes, self.is_before_break):
			# If full screen app found, do not show break screen
			logging.info("Found a skip_break or full-screen window. Skip the break")
			if self.__is_running():
				# Schedule the break again
				Utility.start_thread(self.__scheduler_job)
			return

		# Execute the post-operation
		if self.is_before_break:
			Utility.start_thread(self.__start_break)
		else:
			Utility.start_thread(self.__show_notification)

	def __start_break(self):
		"""
		Start the break screen.
		"""
		# User can disable SafeEyes during notification
		if self.__is_running():
			message = ""
			image = None
			seconds = 0
			audible_alert = None
			if self.__is_long_break():
				logging.info("Count is {}; get a long beak message".format(self.break_count))
				self.long_break_message_index = (self.long_break_message_index + 1) % len(self.long_break_exercises)
				message = self.long_break_exercises[self.long_break_message_index][0]
				seconds = self.long_break_exercises[self.long_break_message_index][1]
				audible_alert = self.long_break_exercises[self.long_break_message_index][2]
				image = self.long_break_exercises[self.long_break_message_index][3]
			else:
				logging.info("Count is {}; get a short beak message".format(self.break_count))
				self.short_break_message_index = (self.short_break_message_index + 1) % len(self.short_break_exercises)
				message = self.short_break_exercises[self.short_break_message_index][0]
				seconds = self.short_break_exercises[self.short_break_message_index][1]
				audible_alert = self.short_break_exercises[self.short_break_message_index][2]
				image = self.short_break_exercises[self.short_break_message_index][3]

			self.context['break_length'] = seconds
			self.context['audible_alert'] = audible_alert
			total_break_time = seconds

			# Show the break screen
			self.start_break(message, image)

			# Use self.active instead of self.__is_running to avoid idle pause interrupting the break
			while seconds and self.active and not self.context['skipped'] and not self.context['postponed']:
				count_down = total_break_time - seconds
				self.context['count_down'] = count_down
				self.on_countdown(count_down, seconds)
				time.sleep(1)    # Sleep for 1 second
				seconds -= 1

			# Loop terminated because of timeout (not skipped) -> Close the break alert
			if not self.context['skipped'] and not self.context['postponed']:
				logging.info("Break is terminated automatically")
				self.end_break(audible_alert)

			# Reset the skipped flag
			self.context['skipped'] = False

			# Resume
			if self.__is_running():
				# Schedule the break again
				Utility.start_thread(self.__scheduler_job)

	def __is_running(self):
		"""
		Tells whether Safe Eyes is running or not.
		"""
		return self.active and self.running

	def __is_long_break(self):
		"""
		Check if the current break is long break or short current
		"""
		return self.break_count == self.no_of_short_breaks_per_long_break - 1

	def __start_idle_monitor(self):
		"""
		Continuously check the system idle time and pause/resume Safe Eyes based on it.
		"""
		while self.active:
			# Wait for 2 seconds
			self.idle_condition.acquire()
			self.idle_condition.wait(2)
			self.idle_condition.release()

			if self.active:
				# Get the system idle time
				system_idle_time = Utility.system_idle_time()
				if system_idle_time >= self.idle_time and self.running:
					logging.info('Pause Safe Eyes due to system idle')
					self.pause()
				elif system_idle_time < self.idle_time and not self.running:
					logging.info('Resume Safe Eyes due to user activity')
					self.resume()
