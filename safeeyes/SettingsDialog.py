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
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkX11, GObject
from safeeyes import Utility

class SettingsDialog:
	"""
		Create and initialize SettingsDialog instance.
	"""
	def __init__(self, config, language, languages, able_to_lock_screen, on_save_settings, glade_file):
		self.config = config
		self.on_save_settings = on_save_settings
		self.languages = []

		builder = Gtk.Builder()
		builder.add_from_file(glade_file)
		builder.connect_signals(self)

		# Get the UI components
		self.window = builder.get_object('window_settings')
		self.spin_short_break_duration = builder.get_object('spin_short_break_duration')
		self.spin_long_break_duration = builder.get_object('spin_long_break_duration')
		self.spin_interval_between_two_breaks = builder.get_object('spin_interval_between_two_breaks')
		self.spin_short_between_long = builder.get_object('spin_short_between_long')
		self.spin_time_to_prepare = builder.get_object('spin_time_to_prepare')
		self.spin_idle_time_to_pause = builder.get_object('spin_idle_time_to_pause')
		self.spin_postpone_duration = builder.get_object('spin_postpone_duration')
		self.switch_strict_break = builder.get_object('switch_strict_break')
		self.switch_postpone = builder.get_object('switch_postpone')
		self.switch_audible_alert = builder.get_object('switch_audible_alert')
		self.cmb_language = builder.get_object('cmb_language')
		self.switch_screen_lock = builder.get_object('switch_screen_lock')
		self.spin_time_to_screen_lock = builder.get_object('spin_time_to_screen_lock')

		# Translate the UI labels
		builder.get_object('lbl_short_break').set_label(language['ui_controls']['short_break_duration'])
		builder.get_object('lbl_long_break').set_label(language['ui_controls']['long_break_duration'])
		builder.get_object('lbl_interval_bettween_breaks').set_label(language['ui_controls']['interval_between_two_breaks'])
		builder.get_object('lbl_short_per_long').set_label(language['ui_controls']['no_of_short_breaks_between_two_long_breaks'])
		builder.get_object('lbl_time_to_prepare').set_label(language['ui_controls']['time_to_prepare_for_break'])
		builder.get_object('lbl_idle_time_to_pause').set_label(language['ui_controls']['idle_time'])
		builder.get_object('lbl_postpone_duration').set_label(language['ui_controls']['postpone_duration'])
		builder.get_object('lbl_allow_postpone').set_label(language['ui_controls']['allow_postpone'])
		builder.get_object('lbl_strict_break').set_label(language['ui_controls']['strict_break'])
		builder.get_object('lbl_audible_alert').set_label(language['ui_controls']['audible_alert'])
		builder.get_object('lbl_language').set_label(language['ui_controls']['language'])
		builder.get_object('lbl_enable_screen_lock').set_label(language['ui_controls']['enable_screen_lock'])
		builder.get_object('lbl_lock_screen_after').set_label(language['ui_controls']['time_to_screen_lock'])
		builder.get_object('btn_cancel').set_label(language['ui_controls']['cancel'])
		builder.get_object('btn_save').set_label(language['ui_controls']['save'])

		# Set the current values of input fields
		self.spin_short_break_duration.set_value(config['short_break_duration'])
		self.spin_long_break_duration.set_value(config['long_break_duration'])
		self.spin_interval_between_two_breaks.set_value(config['break_interval'])
		self.spin_short_between_long.set_value(config['no_of_short_breaks_per_long_break'])
		self.spin_time_to_prepare.set_value(config['pre_break_warning_time'])
		self.spin_idle_time_to_pause.set_value(config['idle_time'])
		self.spin_postpone_duration.set_value(config['postpone_duration'])
		self.switch_strict_break.set_active(config['strict_break'])
		self.switch_audible_alert.set_active(config['audible_alert'])
		self.spin_time_to_screen_lock.set_value(config['time_to_screen_lock'])

		# Enable idle_time_to_pause only if xprintidle is available
		self.spin_idle_time_to_pause.set_sensitive(Utility.command_exist('xprintidle'))

		self.switch_screen_lock.set_sensitive(able_to_lock_screen)
		self.switch_screen_lock.set_active(able_to_lock_screen and config['enable_screen_lock'])
		self.switch_postpone.set_active(config['allow_postpone'] and not config['strict_break'])

		# Update relative states
		self.on_switch_strict_break_activate(self.switch_strict_break, self.switch_strict_break.get_active())
		self.on_switch_screen_lock_activate(self.switch_screen_lock, self.switch_screen_lock.get_active())
		self.on_switch_postpone_activate(self.switch_postpone, self.switch_postpone.get_active())

		# Initialize the language combobox
		language_list_store = Gtk.ListStore(GObject.TYPE_STRING)
		language_index = 2
		lang_code = config['language']

		# Add 'System Language' as the first option
		language_list_store.append([language['ui_controls']['system_language']])
		language_list_store.append(['-'])
		self.languages.append('system')
		self.languages.append('system')	# Dummy record for row separator
		if 'system' == lang_code:
			self.cmb_language.set_active(0)

		for key in sorted(languages.keys()):
			language_list_store.append([languages[key]])
			self.languages.append(key)
			if key == lang_code:
				self.cmb_language.set_active(language_index)
			language_index += 1

		self.cmb_language.set_model(language_list_store)
		self.cmb_language.set_row_separator_func(lambda m,i: m.get_value(i, 0) == '-')
		cell = Gtk.CellRendererText()
		self.cmb_language.pack_start(cell, True)
		self.cmb_language.add_attribute(cell, 'text', 0)


	def show(self):
		"""
		Show the SettingsDialog.
		"""
		self.window.show_all()


	def on_switch_screen_lock_activate(self, switch, state):
		"""
		Event handler to the state change of the screen_lock switch.
		Enable or disable the self.spin_time_to_screen_lock based on the state of the screen_lock switch.
		"""
		self.spin_time_to_screen_lock.set_sensitive(self.switch_screen_lock.get_active())


	def on_switch_strict_break_activate(self, switch, state):
		"""
		Event handler to the state change of the postpone switch.
		Enable or disable the self.spin_postpone_duration based on the state of the postpone switch.
		"""
		strict_break_enable = state #self.switch_strict_break.get_active()
		self.switch_postpone.set_sensitive(not strict_break_enable)
		if strict_break_enable:
			self.switch_postpone.set_active(False)

	def on_switch_postpone_activate(self, switch, state):
		"""
		Event handler to the state change of the postpone switch.
		Enable or disable the self.spin_postpone_duration based on the state of the postpone switch.
		"""
		self.spin_postpone_duration.set_sensitive(self.switch_postpone.get_active())

	def on_window_delete(self, *args):
		"""
		Event handler for Settings dialog close action.
		"""
		self.window.destroy()


	def on_save_clicked(self, button):
		"""
		Event handler for Save button click.
		"""
		self.config['short_break_duration'] = self.spin_short_break_duration.get_value_as_int()
		self.config['long_break_duration'] = self.spin_long_break_duration.get_value_as_int()
		self.config['break_interval'] = self.spin_interval_between_two_breaks.get_value_as_int()
		self.config['no_of_short_breaks_per_long_break'] = self.spin_short_between_long.get_value_as_int()
		self.config['pre_break_warning_time'] = self.spin_time_to_prepare.get_value_as_int()
		self.config['idle_time'] = self.spin_idle_time_to_pause.get_value_as_int()
		self.config['postpone_duration'] = self.spin_postpone_duration.get_value_as_int()
		self.config['strict_break'] = self.switch_strict_break.get_active()
		self.config['audible_alert'] = self.switch_audible_alert.get_active()
		self.config['language'] = self.languages[self.cmb_language.get_active()]
		self.config['time_to_screen_lock'] = self.spin_time_to_screen_lock.get_value_as_int()
		self.config['enable_screen_lock'] = self.switch_screen_lock.get_active()
		self.config['allow_postpone'] = self.switch_postpone.get_active()

		self.on_save_settings(self.config)	# Call the provided save method
		self.window.destroy()	# Close the settings window


	def on_cancel_clicked(self, button):
		"""
		Event handler for Cancel button click.
		"""
		self.window.destroy()
