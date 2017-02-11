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


import time, datetime, threading, sys, subprocess, logging, Utility


"""
	Core of Safe Eyes which runs the scheduler and notifies the breaks.
"""
class SafeEyesCore:

	"""
		Initialize the internal variables of the core.
	"""
	def __init__(self, show_notification, start_break, end_break, on_countdown, update_next_break_info):
		# Initialize the variables
		self.break_count = -1
		self.long_break_message_index = -1
		self.short_break_message_index = -1
		self.skipped = False
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


	"""
		Initialize the internal properties from configuration
	"""
	def initialize(self, config, language):
		logging.info("Initialize the core")
		self.short_break_exercises = [] #language['exercises']['short_break_exercises']
		self.long_break_exercises = [] #language['exercises']['long_break_exercises']

		self.no_of_short_breaks_per_long_break = config['no_of_short_breaks_per_long_break']
		self.pre_break_warning_time = config['pre_break_warning_time']
		self.long_break_duration = config['long_break_duration']
		self.short_break_duration = config['short_break_duration']
		self.break_interval = config['break_interval']
		self.idle_time = config['idle_time']

		for short_break_config in config['short_breaks']:
			name = language['exercises'][short_break_config['name']]
			# break_time = short_break_config['time']
			break_time = short_break_config.get('time', self.short_break_duration)
			# Validate time value
			if not isinstance(break_time, int) or break_time <= 0:
				logging.error('Invalid time in short break: ' + str(short_break_config))
				continue
			
			self.short_break_exercises.append([name, break_time])

		for long_break_config in config['long_breaks']:
			name = language['exercises'][long_break_config['name']]
			break_time = long_break_config.get('time', self.short_break_duration)
			# Validate time value
			if not break_time:
				break_time = self.short_break_duration
			elif not isinstance(break_time, int) or break_time <= 0:
				logging.error('Invalid time in short break: ' + str(long_break_config))
				continue
			else:
				break_time = break_time * 60	# Convert to seconds
			
			self.long_break_exercises.append([name, break_time])


	"""
		Start Safe Eyes is it is not running already.
	"""
	def start(self):
		with self.lock:
			if not self.active:
				logging.info("Scheduling next break")
				self.active = True
				self.running = True
				Utility.start_thread(self.__scheduler_job)
				Utility.start_thread(self.__start_idle_monitor)


	"""
		Stop Safe Eyes if it is running.
	"""
	def stop(self):
		with self.lock:
			if self.active:
				logging.info("Stop the core")
				# Reset the state properties in case of restart
				# self.break_count = 0
				# self.long_break_message_index = -1
				# self.short_break_message_index = -1

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


	"""
		Pause Safe Eyes if it is running.
	"""
	def pause(self):
		with self.lock:
			if self.active and self.running:
				self.notification_condition.acquire()
				self.running = False
				self.notification_condition.notify_all()
				self.notification_condition.release()


	"""
		Resume Safe Eyes if it is not running.
	"""
	def resume(self):
		with self.lock:
			if self.active and not self.running:
				self.running = True
				Utility.start_thread(self.__scheduler_job)


	"""
		User skipped the break using Skip button
	"""
	def skip_break(self):
		self.skipped = True


	"""
		Scheduler task to execute during every interval
	"""
	def __scheduler_job(self):
		if not self.__is_running():
			return

		next_break_time = datetime.datetime.now() + datetime.timedelta(minutes=self.break_interval)
		self.update_next_break_info(next_break_time)


		# Wait for the pre break warning period
		logging.info("Pre-break waiting for {} minutes".format(self.break_interval))
		self.notification_condition.acquire()
		self.notification_condition.wait(self.break_interval * 60)	# In minutes
		self.notification_condition.release()

		logging.info("Pre-break waiting is over")

		if not self.__is_running():
			return

		logging.info("Ready to show the break")

		Utility.execute_main_thread(self.__process_job)

	"""
		Used to process the job in default thread because __is_full_screen_app_found must be run by default thread
	"""
	def __process_job(self):
		if Utility.is_full_screen_app_found():
			# If full screen app found, do not show break screen
			logging.info("Found a full-screen application. Skip the break")
			if self.__is_running():
				# Schedule the break again
				Utility.start_thread(self.__scheduler_job)
			return

		self.break_count = ((self.break_count + 1) % self.no_of_short_breaks_per_long_break)

		Utility.start_thread(self.__notify_and_start_break)

	"""
		Show notification and start the break after given number of seconds
	"""
	def __notify_and_start_break(self):
		# Show a notification
		self.show_notification()

		logging.info("Wait for {} seconds which is the time to prepare".format(self.pre_break_warning_time))
		# Wait for the pre break warning period
		self.notification_condition.acquire()
		self.notification_condition.wait(self.pre_break_warning_time)
		self.notification_condition.release()

		# User can disable SafeEyes during notification
		if self.__is_running():
			message = ""
			seconds = 0
			if self.__is_long_break():
				logging.info("Count is {}; get a long beak message".format(self.break_count))
				self.long_break_message_index = (self.long_break_message_index + 1) % len(self.long_break_exercises)
				message = self.long_break_exercises[self.long_break_message_index][0]
				seconds = self.long_break_exercises[self.long_break_message_index][1]
			else:
				logging.info("Count is {}; get a short beak message".format(self.break_count))
				self.short_break_message_index = (self.short_break_message_index + 1) % len(self.short_break_exercises)
				message = self.short_break_exercises[self.short_break_message_index][0]
				seconds = self.short_break_exercises[self.short_break_message_index][1]
			
			# Show the break screen
			self.start_break(message)		

			# Use self.active instead of self.__is_running to avoid idle pause interrupting the break
			while seconds and self.active and not self.skipped:
				mins, secs = divmod(seconds, 60)
				timeformat = '{:02d}:{:02d}'.format(mins, secs)
				self.on_countdown(timeformat)
				time.sleep(1)	# Sleep for 1 second
				seconds -= 1

			# Loop terminated because of timeout (not skipped) -> Close the break alert
			if not self.skipped:
				logging.info("Break wasn't skipped. Automatically terminating the break")
				self.end_break()

			# Resume
			if self.__is_running():
				# Schedule the break again
				Utility.start_thread(self.__scheduler_job)

			self.skipped = False


	"""
		Tells whether Safe Eyes is running or not.
	"""
	def __is_running(self):
		return self.active and self.running


	"""
		Check if the current break is long break or short current
	"""
	def __is_long_break(self):
		return self.break_count == self.no_of_short_breaks_per_long_break - 1


	"""
		Continuously check the system idle time and pause/resume Safe Eyes based on it.
	"""
	def __start_idle_monitor(self):
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
