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

import gi
gi.require_version('Gdk', '3.0')
from gi.repository import  Gdk, Gio, GLib
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
import time, threading, sys, subprocess, logging

logging.basicConfig()

class SafeEyesCore:
	scheduler_job_id = "safe_eyes_scheduler"
	break_count = 0
	long_break_message_index = 0
	short_break_message_index = 0

	def __init__(self, show_alert, start_break, end_break, on_countdown):
		self.skipped = False
		self.scheduler = None
		self.show_alert = show_alert
		self.start_break = start_break
		self.end_break = end_break
		self.on_countdown = on_countdown

	"""
		Initialize the internal properties from configuration
	"""
	def initialize(self, config):
		self.short_break_messages = config['short_break_messages']
		self.long_break_messages = config['long_break_messages']
		self.no_of_short_breaks_per_long_break = config['no_of_short_breaks_per_long_break']
		self.pre_break_warning_time = config['pre_break_warning_time']
		self.long_break_duration = config['long_break_duration']
		self.short_break_duration = config['short_break_duration']
		self.break_interval = config['break_interval']

	"""
		Scheduler task to execute during every interval
	"""
	def scheduler_job(self):
		if not self.active:
			return

		# Pause the scheduler until the break
		if self.scheduler:
			self.scheduler.pause_job(self.scheduler_job_id)

		GLib.idle_add(lambda: self.process_job())


	def process_job(self):
		if self.is_full_screen_app_found():
			if self.scheduler:
				self.scheduler.resume_job(self.scheduler_job_id)
			return

		self.break_count = ((self.break_count + 1) % self.no_of_short_breaks_per_long_break)

		thread = threading.Thread(target=self.show_notification)
		thread.start()

	def show_notification(self):
		# Show a notification
		self.show_alert()

		# Wait for the pre break warning period
		time.sleep(self.pre_break_warning_time)

		if self.active:
			message = ""
			if self.is_long_break():
				self.long_break_message_index = (self.long_break_message_index + 1) % len(self.long_break_messages)
				message = self.long_break_messages[self.long_break_message_index]
			else:
				self.short_break_message_index = (self.short_break_message_index + 1) % len(self.short_break_messages)
				message = self.short_break_messages[self.short_break_message_index]
			
			self.start_break(message)
			# Start the countdown
			thread = threading.Thread(target=self.countdown)
			thread.start()

	"""
		Countdown the seconds of break interval, call the on_countdown and finally call the end_break method
	"""
	def countdown(self):
		seconds = 0
		if self.is_long_break():
			seconds = self.long_break_duration
		else:
			seconds = self.short_break_duration

		while seconds and self.active and not self.skipped:
			mins, secs = divmod(seconds, 60)
			timeformat = '{:02d}:{:02d}'.format(mins, secs)
			self.on_countdown(timeformat)
			time.sleep(1)	# Sleep for 1 second
			seconds -= 1

		# Timeout -> Close the break alert
		if not self.skipped:
			self.end_break()

		# Resume the scheduler
		if self.active:
			if self.scheduler:
				self.scheduler.resume_job(self.scheduler_job_id)

		self.skipped = False

	"""
		Check if the current break is long break or short current
	"""
	def is_long_break(self):
		return self.break_count == self.no_of_short_breaks_per_long_break - 1

	def reset(self):
		self.skipped = True

	"""
		Resume the timer
	"""
	def resume(self):
		if not self.active:
			self.active = True
			if self.scheduler:
				self.scheduler.resume_job(self.scheduler_job_id)

	"""
		Pause the timer
	"""
	def pause(self):
		if self.active:
			self.active = False
			if self.scheduler:
				self.scheduler.pause_job(self.scheduler_job_id)

	def stop(self):
		if self.scheduler:
			self.active = False
			self.scheduler.pause_job(self.scheduler_job_id)
			self.scheduler.shutdown(wait=False)
			self.scheduler = None
	
	"""
		Start the timer
	"""
	def start(self):
		self.active = True
		if not self.scheduler:
			self.scheduler = BackgroundScheduler()
			self.scheduler.add_job(self.scheduler_job, 'interval', minutes=self.break_interval, id=self.scheduler_job_id)
		self.scheduler.start()

	"""
		Check for full-screen applications
	"""
	def is_full_screen_app_found(self):
		screen = Gdk.Screen.get_default()
		active_xid = str(screen.get_active_window().get_xid())
		cmdlist = ['xprop', '-root', '-notype','-id',active_xid, '_NET_WM_STATE']
		
		try:
			stdout = subprocess.check_output(cmdlist)
		except subprocess.CalledProcessError:
			pass
		else:
			if stdout:
				return 'FULLSCREEN' in stdout

