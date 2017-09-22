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
from safeeyes import Utility

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


SETTINGS_DIALOG_GLADE = os.path.join(Utility.BIN_DIRECTORY, "glade/settings_dialog.glade")
SETTINGS_DIALOG_PLUGIN_GLADE = os.path.join(Utility.BIN_DIRECTORY, "glade/settings_plugin.glade")
SETTINGS_BREAK_ITEM_GLADE = os.path.join(Utility.BIN_DIRECTORY, "glade/item_break.glade")
SETTINGS_PLUGIN_ITEM_GLADE = os.path.join(Utility.BIN_DIRECTORY, "glade/item_plugin.glade")
SETTINGS_ITEM_INT_GLADE = os.path.join(Utility.BIN_DIRECTORY, "glade/item_int.glade")
SETTINGS_ITEM_TEXT_GLADE = os.path.join(Utility.BIN_DIRECTORY, "glade/item_text.glade")
SETTINGS_ITEM_BOOL_GLADE = os.path.join(Utility.BIN_DIRECTORY, "glade/item_bool.glade")

class SettingsDialog(object):
    """
        Create and initialize SettingsDialog instance.
    """
    def __init__(self, config, on_save_settings):
        self.config = config
        self.on_save_settings = on_save_settings
        self.plugin_switches = {}

        builder = Utility.create_gtk_builder(SETTINGS_DIALOG_GLADE)
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
        Create an entry for break to be listed in the break tab.
        """
        builder = Utility.create_gtk_builder(SETTINGS_BREAK_ITEM_GLADE)
        builder.get_object('lbl_name').set_label(name)
        box = builder.get_object('box')
        box.set_visible(True)
        return box

    def __create_plugin_item(self, plugin_config):
        """
        Create an entry for plugin to be listed in the plugin tab.
        """
        builder = Utility.create_gtk_builder(SETTINGS_PLUGIN_ITEM_GLADE)
        builder.get_object('lbl_plugin_name').set_label(plugin_config['meta']['name'])
        builder.get_object('lbl_plugin_description').set_label(plugin_config['meta']['description'])
        switch_enable = builder.get_object('switch_enable')
        btn_properties = builder.get_object('btn_properties')
        switch_enable.set_active(plugin_config['enabled'])
        self.plugin_switches[plugin_config['id']] = switch_enable
        if plugin_config['icon']:
            builder.get_object('img_plugin_icon').set_from_file(plugin_config['icon'])
        if plugin_config['settings']:
            btn_properties.set_sensitive(True)
            btn_properties.connect('clicked', lambda button: self.__show_plugins_properties_dialog(plugin_config))
        else:
            btn_properties.set_sensitive(False)
        box = builder.get_object('box')
        box.set_visible(True)
        return box

    def __show_plugins_properties_dialog(self, plugin_config):
        """
        Show the PluginProperties dialog
        """
        dialog = PluginPropertiesDialog(plugin_config)
        dialog.show()

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


class PluginPropertiesDialog(object):
    """
    Builds a property dialog based on the configuration of a plugin.
    """
    def __init__(self, config):
        self.config = config
        self.property_controls = []

        builder = Utility.create_gtk_builder(SETTINGS_DIALOG_PLUGIN_GLADE)
        builder.connect_signals(self)
        self.window = builder.get_object('dialog_settings_plugin')
        box_settings = builder.get_object('box_settings')
        for setting in config['settings']:
            if setting['type'].upper() == 'INT':
                box_settings.pack_start(self.__load_int_item(setting['label'], setting['id'], setting['safeeyes_config']), False, False, 0)
            elif setting['type'].upper() == 'TEXT':
                box_settings.pack_start(self.__load_text_item(setting['label'], setting['id'], setting['safeeyes_config']), False, False, 0)
            elif setting['type'].upper() == 'BOOL':
                box_settings.pack_start(self.__load_bool_item(setting['label'], setting['id'], setting['safeeyes_config']), False, False, 0)
    
    def __load_int_item(self, name, key, settings):
        """
        Load the UI control for int property.
        """
        builder = Utility.create_gtk_builder(SETTINGS_ITEM_INT_GLADE)
        builder.get_object('lbl_name').set_label(name)
        spin_value = builder.get_object('spin_value')
        spin_value.set_value(settings[key])
        box = builder.get_object('box')
        box.set_visible(True)
        self.property_controls.append({'key': key, 'settings': settings, 'value': spin_value.get_value})
        return box

    def __load_text_item(self, name, key, settings):
        """
        Load the UI control for text property.
        """
        builder = Utility.create_gtk_builder(SETTINGS_ITEM_TEXT_GLADE)
        builder.get_object('lbl_name').set_label(name)
        txt_value = builder.get_object('txt_value')
        txt_value.set_text(settings[key])
        box = builder.get_object('box')
        box.set_visible(True)
        self.property_controls.append({'key': key, 'settings': settings, 'value': txt_value.get_text})
        return box

    def __load_bool_item(self, name, key, settings):
        """
        Load the UI control for boolean property.
        """
        builder = Utility.create_gtk_builder(SETTINGS_ITEM_BOOL_GLADE)
        builder.get_object('lbl_name').set_label(name)
        switch_value = builder.get_object('switch_value')
        switch_value.set_active(settings[key])
        box = builder.get_object('box')
        box.set_visible(True)
        self.property_controls.append({'key': key, 'settings': settings, 'value': switch_value.get_active})
        return box

    def on_window_delete(self, *args):
        """
        Event handler for Properties dialog close action.
        """
        for property_control in self.property_controls:
            property_control['settings'][property_control['key']] = property_control['value']()
        self.window.destroy()

    def show(self):
        """
        Show the Properties dialog.
        """
        self.window.show_all()


