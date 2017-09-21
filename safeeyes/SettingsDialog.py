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

import os

import gi
from gi.repository import Gtk
from safeeyes import Utility

gi.require_version('Gtk', '3.0')

SETTINGS_DIALOG_GLADE = os.path.join(Utility.BIN_DIRECTORY, "glade/settings_dialog.glade")
SETTINGS_BREAK_ITEM_GLADE = os.path.join(Utility.BIN_DIRECTORY, "glade/item_break.glade")
SETTINGS_PLUGIN_ITEM_GLADE = os.path.join(Utility.BIN_DIRECTORY, "glade/item_plugin.glade")

class SettingsDialog(object):
    """
        Create and initialize SettingsDialog instance.
    """
    def __init__(self, config, on_save_settings):
        self.config = config
        self.on_save_settings = on_save_settings
        self.plugin_switches = {}

        builder = Gtk.Builder()
        builder.set_translation_domain('safeeyes')
        builder.add_from_file(SETTINGS_DIALOG_GLADE)
        builder.connect_signals(self)

        self.window = builder.get_object('window_settings')
        box_short_breaks = builder.get_object('box_short_breaks')
        box_long_breaks = builder.get_object('box_long_breaks')
        box_plugins = builder.get_object('box_plugins')
        for short_break in config['short_breaks']:
            box_short_breaks.pack_start(self.__create_break_item(_(short_break['name'])), False, False, 0)
        for long_break in config['long_breaks']:
            box_long_breaks.pack_start(self.__create_break_item(_(long_break['name'])), False, False, 0)
        
        for plugin_config in Utility.load_plugins_config_gobi(config):
            box_plugins.pack_start(self.__create_plugin_item(plugin_config), False, False, 0)
        
        self.spin_short_break_duration = builder.get_object('spin_short_break_duration')
        self.spin_long_break_duration = builder.get_object('spin_long_break_duration')
        self.spin_interval_between_two_breaks = builder.get_object('spin_interval_between_two_breaks')
        self.spin_short_between_long = builder.get_object('spin_short_between_long')
        self.spin_time_to_prepare = builder.get_object('spin_time_to_prepare')
        self.spin_postpone_duration = builder.get_object('spin_postpone_duration')
        self.spin_disable_keyboard_shortcut = builder.get_object('spin_disable_keyboard_shortcut')
        self.switch_strict_break = builder.get_object('switch_strict_break')
        self.switch_postpone = builder.get_object('switch_postpone')

        # Set the current values of input fields
        self.spin_short_break_duration.set_value(config['short_break_duration'])
        self.spin_long_break_duration.set_value(config['long_break_duration'])
        self.spin_interval_between_two_breaks.set_value(config['break_interval'])
        self.spin_short_between_long.set_value(config['no_of_short_breaks_per_long_break'])
        self.spin_time_to_prepare.set_value(config['pre_break_warning_time'])
        self.spin_postpone_duration.set_value(config['postpone_duration'])
        self.spin_disable_keyboard_shortcut.set_value(config['shortcut_disable_time'])
        self.switch_strict_break.set_active(config['strict_break'])
        self.switch_postpone.set_active(config['allow_postpone'] and not config['strict_break'])

        # Update relative states
        # GtkSwitch state-set signal is available only from 3.14
        if Gtk.get_minor_version() >= 14:
            self.switch_strict_break.connect('state-set', self.on_switch_strict_break_activate)
            self.switch_postpone.connect('state-set', self.on_switch_postpone_activate)
            self.on_switch_strict_break_activate(self.switch_strict_break, self.switch_strict_break.get_active())
            self.on_switch_postpone_activate(self.switch_postpone, self.switch_postpone.get_active())

    def __create_break_item(self, name):
        """
        """
        builder = Gtk.Builder()
        builder.add_from_file(SETTINGS_BREAK_ITEM_GLADE)
        builder.get_object('lbl_name').set_label(name)
        box = builder.get_object('box')
        box.set_visible(True)
        return box

    def __create_plugin_item(self, plugin_config):
        """
        """
        builder = Gtk.Builder()
        builder.add_from_file(SETTINGS_PLUGIN_ITEM_GLADE)
        builder.get_object('lbl_plugin_name').set_label(plugin_config['meta']['name'])
        builder.get_object('lbl_plugin_description').set_label(plugin_config['meta']['description'])
        switch_enable = builder.get_object('switch_enable')
        switch_enable.set_active(plugin_config['enabled'])
        self.plugin_switches[plugin_config['id']] = switch_enable
        if plugin_config['icon']:
            builder.get_object('img_plugin_icon').set_from_file(plugin_config['icon'])
        box = builder.get_object('box')
        box.set_visible(True)
        return box

    def show(self):
        """
        Show the SettingsDialog.
        """
        self.window.show_all()

    def on_switch_strict_break_activate(self, switch, state):
        """
        Event handler to the state change of the postpone switch.
        Enable or disable the self.spin_postpone_duration based on the state of the postpone switch.
        """
        strict_break_enable = state    # self.switch_strict_break.get_active()
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
        self.config['short_break_duration'] = self.spin_short_break_duration.get_value_as_int()
        self.config['long_break_duration'] = self.spin_long_break_duration.get_value_as_int()
        self.config['break_interval'] = self.spin_interval_between_two_breaks.get_value_as_int()
        self.config['no_of_short_breaks_per_long_break'] = self.spin_short_between_long.get_value_as_int()
        self.config['pre_break_warning_time'] = self.spin_time_to_prepare.get_value_as_int()
        self.config['postpone_duration'] = self.spin_postpone_duration.get_value_as_int()
        self.config['shortcut_disable_time'] = self.spin_disable_keyboard_shortcut.get_value_as_int()
        self.config['strict_break'] = self.switch_strict_break.get_active()
        self.config['allow_postpone'] = self.switch_postpone.get_active()
        for plugin in self.config['plugins']:
            if plugin['id'] in self.plugin_switches:
                plugin['enabled'] = self.plugin_switches[plugin['id']].get_active()
        self.on_save_settings(self.config)    # Call the provided save method
        self.window.destroy()

    def __show_message_dialog(self, primary_text, secondary_text):
        """
        Show a popup message dialog.
        """
        dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.OK, primary_text)
        dialog.format_secondary_text(secondary_text)
        dialog.run()
        dialog.destroy()
