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

import math
import os

import gi
from safeeyes import utility
from safeeyes.model import Config

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GdkPixbuf


SETTINGS_DIALOG_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/settings_dialog.glade")
SETTINGS_DIALOG_PLUGIN_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/settings_plugin.glade")
SETTINGS_DIALOG_BREAK_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/settings_break.glade")
SETTINGS_DIALOG_NEW_BREAK_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/new_break.glade")
SETTINGS_BREAK_ITEM_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_break.glade")
SETTINGS_PLUGIN_ITEM_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_plugin.glade")
SETTINGS_ITEM_INT_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_int.glade")
SETTINGS_ITEM_TEXT_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_text.glade")
SETTINGS_ITEM_BOOL_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_bool.glade")


class SettingsDialog:
    """
        Create and initialize SettingsDialog instance.
    """

    def __init__(self, config, on_save_settings):
        self.config = config
        self.on_save_settings = on_save_settings
        self.plugin_switches = {}
        self.plugin_map = {}
        self.last_short_break_interval = config.get('short_break_interval')
        self.initializing = True
        self.infobar_long_break_shown = False
        self.warn_bar_rpc_server_shown = False

        builder = utility.create_gtk_builder(SETTINGS_DIALOG_GLADE)
        builder.connect_signals(self)

        self.window = builder.get_object('window_settings')
        self.box_short_breaks = builder.get_object('box_short_breaks')
        self.box_long_breaks = builder.get_object('box_long_breaks')
        self.box_plugins = builder.get_object('box_plugins')
        self.popover = builder.get_object('popover')

        self.spin_short_break_duration = builder.get_object('spin_short_break_duration')
        self.spin_long_break_duration = builder.get_object('spin_long_break_duration')
        self.spin_short_break_interval = builder.get_object('spin_short_break_interval')
        self.spin_long_break_interval = builder.get_object('spin_long_break_interval')
        self.spin_time_to_prepare = builder.get_object('spin_time_to_prepare')
        self.spin_postpone_duration = builder.get_object('spin_postpone_duration')
        self.spin_disable_keyboard_shortcut = builder.get_object('spin_disable_keyboard_shortcut')
        self.switch_strict_break = builder.get_object('switch_strict_break')
        self.switch_random_order = builder.get_object('switch_random_order')
        self.switch_postpone = builder.get_object('switch_postpone')
        self.switch_persist = builder.get_object('switch_persist')
        self.switch_rpc_server = builder.get_object('switch_rpc_server')
        self.info_bar_long_break = builder.get_object("info_bar_long_break")
        self.warn_bar_rpc_server = builder.get_object("warn_bar_rpc_server")
        self.info_bar_long_break.hide()
        self.warn_bar_rpc_server.hide()

        # Set the current values of input fields
        self.__initialize(config)

        # Update relative states
        # GtkSwitch state-set signal is available only from 3.14
        if Gtk.get_minor_version() >= 14:
            # Add event listener to postpone switch
            self.switch_postpone.connect('state-set', self.on_switch_postpone_activate)
            self.on_switch_postpone_activate(self.switch_postpone, self.switch_postpone.get_active())
            # Add event listener to RPC server switch
            self.switch_rpc_server.connect('state-set', self.on_switch_rpc_server_activate)
            self.on_switch_rpc_server_activate(self.switch_rpc_server, self.switch_rpc_server.get_active())
        self.initializing = False

    def __initialize(self, config):
        # Don't show infobar for changes made internally
        self.infobar_long_break_shown = True
        for short_break in config.get('short_breaks'):
            self.__create_break_item(short_break, True)
        for long_break in config.get('long_breaks'):
            self.__create_break_item(long_break, False)

        for plugin_config in utility.load_plugins_config(config):
            self.box_plugins.pack_start(self.__create_plugin_item(plugin_config), False, False, 0)
            
        self.spin_short_break_duration.set_value(config.get('short_break_duration'))
        self.spin_long_break_duration.set_value(config.get('long_break_duration'))
        self.spin_short_break_interval.set_value(config.get('short_break_interval'))
        self.spin_long_break_interval.set_value(config.get('long_break_interval'))
        self.spin_time_to_prepare.set_value(config.get('pre_break_warning_time'))
        self.spin_postpone_duration.set_value(config.get('postpone_duration'))
        self.spin_disable_keyboard_shortcut.set_value(config.get('shortcut_disable_time'))
        self.switch_strict_break.set_active(config.get('strict_break'))
        self.switch_random_order.set_active(config.get('random_order'))
        self.switch_postpone.set_active(config.get('allow_postpone'))
        self.switch_persist.set_active(config.get('persist_state'))
        self.switch_rpc_server.set_active(config.get('use_rpc_server'))
        self.infobar_long_break_shown = False

    def __create_break_item(self, break_config, is_short):
        """
        Create an entry for break to be listed in the break tab.
        """
        parent_box = self.box_long_breaks
        if is_short:
            parent_box = self.box_short_breaks
        builder = utility.create_gtk_builder(SETTINGS_BREAK_ITEM_GLADE)
        box = builder.get_object('box')
        lbl_name = builder.get_object('lbl_name')
        lbl_name.set_label(_(break_config['name']))
        btn_properties = builder.get_object('btn_properties')
        btn_properties.connect(
            'clicked',
            lambda button: self.__show_break_properties_dialog(
                break_config,
                is_short,
                self.config,
                lambda cfg: lbl_name.set_label(_(cfg['name'])),
                lambda is_short, break_config: self.__create_break_item(break_config, is_short),
                lambda: parent_box.remove(box)
            )
        )
        btn_delete = builder.get_object('btn_delete')
        btn_delete.connect(
            'clicked',
            lambda button: self.__delete_break(
                break_config,
                is_short,
                lambda: parent_box.remove(box),
            )
        )
        box.set_visible(True)
        parent_box.pack_start(box, False, False, 0)
        return box

    def on_reset_menu_clicked(self, button):
        self.popover.hide()
        def __confirmation_dialog_response(widget, response_id):
            if response_id == Gtk.ResponseType.OK:
                utility.reset_config()
                self.config = Config()
                # Remove breaks from the container
                self.box_short_breaks.foreach(lambda element: self.box_short_breaks.remove(element))
                self.box_long_breaks.foreach(lambda element: self.box_long_breaks.remove(element))
                # Remove plugins from the container
                self.box_plugins.foreach(lambda element: self.box_plugins.remove(element))
                # Initialize again
                self.__initialize(self.config)
            widget.destroy()

        messagedialog = Gtk.MessageDialog(parent=self.window,
                                          flags=Gtk.DialogFlags.MODAL,
                                          type=Gtk.MessageType.WARNING,
                                          buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                   _("Reset"), Gtk.ResponseType.OK),
                                          message_format=_("Are you sure you want to reset all settings to default?"))
        messagedialog.connect("response", __confirmation_dialog_response)
        messagedialog.format_secondary_text(_("You can't undo this action."))
        messagedialog.show()

    def __delete_break(self, break_config, is_short, on_remove):
        """
        Remove the break after a confirmation.
        """

        def __confirmation_dialog_response(widget, response_id):
            if response_id == Gtk.ResponseType.OK:
                if is_short:
                    self.config.get('short_breaks').remove(break_config)
                else:
                    self.config.get('long_breaks').remove(break_config)
                on_remove()
            widget.destroy()

        messagedialog = Gtk.MessageDialog(parent=self.window,
                                          flags=Gtk.DialogFlags.MODAL,
                                          type=Gtk.MessageType.WARNING,
                                          buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                   _("Delete"), Gtk.ResponseType.OK),
                                          message_format=_("Are you sure you want to delete this break?"))
        messagedialog.connect("response", __confirmation_dialog_response)
        messagedialog.format_secondary_text(_("You can't undo this action."))
        messagedialog.show()

    def __create_plugin_item(self, plugin_config):
        """
        Create an entry for plugin to be listed in the plugin tab.
        """
        builder = utility.create_gtk_builder(SETTINGS_PLUGIN_ITEM_GLADE)
        lbl_plugin_name = builder.get_object('lbl_plugin_name')
        lbl_plugin_description = builder.get_object('lbl_plugin_description')
        switch_enable = builder.get_object('switch_enable')
        btn_properties = builder.get_object('btn_properties')
        lbl_plugin_name.set_label(_(plugin_config['meta']['name']))
        switch_enable.set_active(plugin_config['enabled'])
        if plugin_config['error']:
            lbl_plugin_description.set_label(_(plugin_config['meta']['description']))
            lbl_plugin_name.set_sensitive(False)
            lbl_plugin_description.set_sensitive(False)
            switch_enable.set_sensitive(False)
        else:
            lbl_plugin_description.set_label(_(plugin_config['meta']['description']))
        self.plugin_switches[plugin_config['id']] = switch_enable
        if plugin_config.get('break_override_allowed', False):
            self.plugin_map[plugin_config['id']] = plugin_config['meta']['name']
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
        dialog = PluginSettingsDialog(plugin_config)
        dialog.show()

    def __show_break_properties_dialog(self, break_config, is_short, parent, on_close, on_add, on_remove):
        """
        Show the BreakProperties dialog
        """
        dialog = BreakSettingsDialog(break_config, is_short, parent, self.plugin_map, on_close, on_add, on_remove)
        dialog.show()

    def show(self):
        """
        Show the SettingsDialog.
        """
        self.window.show_all()

    def on_switch_postpone_activate(self, switch, state):
        """
        Event handler to the state change of the postpone switch.
        Enable or disable the self.spin_postpone_duration based on the state of the postpone switch.
        """
        self.spin_postpone_duration.set_sensitive(self.switch_postpone.get_active())

    def on_spin_short_break_interval_change(self, spin_button, *value):
        """
        Event handler for value change of short break interval.
        """
        short_break_interval = self.spin_short_break_interval.get_value_as_int()
        long_break_interval = self.spin_long_break_interval.get_value_as_int()
        self.spin_long_break_interval.set_range(short_break_interval * 2, 120)
        self.spin_long_break_interval.set_increments(short_break_interval, short_break_interval * 2)
        self.spin_long_break_interval.set_value(short_break_interval * math.ceil(long_break_interval / self.last_short_break_interval))
        self.last_short_break_interval = short_break_interval
        if not self.initializing and not self.infobar_long_break_shown:
            self.infobar_long_break_shown = True
            self.info_bar_long_break.show()

    def on_spin_long_break_interval_change(self, spin_button, *value):
        """
        Event handler for value change of long break interval.
        """
        if not self.initializing and not self.infobar_long_break_shown:
            self.infobar_long_break_shown = True
            self.info_bar_long_break.show()

    def on_info_bar_long_break_close(self, infobar, *user_data):
        """
        Event handler for info bar close action.
        """
        self.info_bar_long_break.hide()

    def on_switch_rpc_server_activate(self, switch, enabled):
        """
        Event handler to the state change of the rpc server switch.
        Show or hide the self.warn_bar_rpc_server based on the state of the rpc server.
        """
        if not self.initializing and not enabled and not self.warn_bar_rpc_server_shown:
            self.warn_bar_rpc_server_shown = True
            self.warn_bar_rpc_server.show()
        if enabled:
            self.warn_bar_rpc_server.hide()

    def on_warn_bar_rpc_server_close(self, warnbar, *user_data):
        """
        Event handler for warning bar close action.
        """
        self.warn_bar_rpc_server.hide()

    def add_break(self, button):
        """
        Event handler for add break button.
        """
        dialog = NewBreakDialog(self.config, lambda is_short, break_config: self.__create_break_item(break_config, is_short))
        dialog.show()

    def on_window_delete(self, *args):
        """
        Event handler for Settings dialog close action.
        """
        self.config.set('short_break_duration', self.spin_short_break_duration.get_value_as_int())
        self.config.set('long_break_duration', self.spin_long_break_duration.get_value_as_int())
        self.config.set('short_break_interval', self.spin_short_break_interval.get_value_as_int())
        self.config.set('long_break_interval', self.spin_long_break_interval.get_value_as_int())
        self.config.set('pre_break_warning_time', self.spin_time_to_prepare.get_value_as_int())
        self.config.set('postpone_duration', self.spin_postpone_duration.get_value_as_int())
        self.config.set('shortcut_disable_time', self.spin_disable_keyboard_shortcut.get_value_as_int())
        self.config.set('strict_break', self.switch_strict_break.get_active())
        self.config.set('random_order', self.switch_random_order.get_active())
        self.config.set('allow_postpone', self.switch_postpone.get_active())
        self.config.set('persist_state', self.switch_persist.get_active())
        self.config.set('use_rpc_server', self.switch_rpc_server.get_active())
        for plugin in self.config.get('plugins'):
            if plugin['id'] in self.plugin_switches:
                plugin['enabled'] = self.plugin_switches[plugin['id']].get_active()

        self.on_save_settings(self.config)    # Call the provided save method
        self.window.destroy()


class PluginSettingsDialog:
    """
    Builds a settings dialog based on the configuration of a plugin.
    """

    def __init__(self, config):
        self.config = config
        self.property_controls = []

        builder = utility.create_gtk_builder(SETTINGS_DIALOG_PLUGIN_GLADE)
        builder.connect_signals(self)
        self.window = builder.get_object('dialog_settings_plugin')
        box_settings = builder.get_object('box_settings')
        self.window.set_title(_('Plugin Settings'))
        for setting in config.get('settings'):
            if setting['type'].upper() == 'INT':
                box_settings.pack_start(self.__load_int_item(setting['label'], setting['id'], setting['safeeyes_config'], setting.get('min', 0), setting.get('max', 120)), False, False, 0)
            elif setting['type'].upper() == 'TEXT':
                box_settings.pack_start(self.__load_text_item(setting['label'], setting['id'], setting['safeeyes_config']), False, False, 0)
            elif setting['type'].upper() == 'BOOL':
                box_settings.pack_start(self.__load_bool_item(setting['label'], setting['id'], setting['safeeyes_config']), False, False, 0)

    def __load_int_item(self, name, key, settings, min_value, max_value):
        """
        Load the UI control for int property.
        """
        builder = utility.create_gtk_builder(SETTINGS_ITEM_INT_GLADE)
        builder.get_object('lbl_name').set_label(_(name))
        spin_value = builder.get_object('spin_value')
        spin_value.set_range(min_value, max_value)
        spin_value.set_value(settings[key])
        box = builder.get_object('box')
        box.set_visible(True)
        self.property_controls.append({'key': key, 'settings': settings, 'value': spin_value.get_value})
        return box

    def __load_text_item(self, name, key, settings):
        """
        Load the UI control for text property.
        """
        builder = utility.create_gtk_builder(SETTINGS_ITEM_TEXT_GLADE)
        builder.get_object('lbl_name').set_label(_(name))
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
        builder = utility.create_gtk_builder(SETTINGS_ITEM_BOOL_GLADE)
        builder.get_object('lbl_name').set_label(_(name))
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


class BreakSettingsDialog:
    """
    Builds a settings dialog based on the configuration of a plugin.
    """

    def __init__(self, break_config, is_short, parent_config, plugin_map, on_close, on_add, on_remove):
        self.break_config = break_config
        self.parent_config = parent_config
        self.plugin_check_buttons = {}
        self.on_close = on_close
        self.is_short = is_short
        self.on_add = on_add
        self.on_remove = on_remove

        builder = utility.create_gtk_builder(SETTINGS_DIALOG_BREAK_GLADE)
        builder.connect_signals(self)
        self.window = builder.get_object('dialog_settings_break')
        self.txt_break = builder.get_object('txt_break')
        self.switch_override_interval = builder.get_object('switch_override_interval')
        self.switch_override_duration = builder.get_object('switch_override_duration')
        self.switch_override_plugins = builder.get_object('switch_override_plugins')
        self.spin_interval = builder.get_object('spin_interval')
        self.spin_duration = builder.get_object('spin_duration')
        self.img_break = builder.get_object('img_break')
        self.cmb_type = builder.get_object('cmb_type')

        grid_plugins = builder.get_object('grid_plugins')
        list_types = builder.get_object('lst_break_types')

        interval_overriden = break_config.get('interval', None) is not None
        duration_overriden = break_config.get('duration', None) is not None
        plugins_overriden = break_config.get('plugins', None) is not None

        # Set the values
        self.window.set_title(_('Break Settings'))
        self.txt_break.set_text(_(break_config['name']))
        self.switch_override_interval.set_active(interval_overriden)
        self.switch_override_duration.set_active(duration_overriden)
        self.switch_override_plugins.set_active(plugins_overriden)
        self.cmb_type.set_active(0 if is_short else 1)
        list_types[0][0] = _(list_types[0][0])
        list_types[1][0] = _(list_types[1][0])

        if interval_overriden:
            self.spin_interval.set_value(break_config['interval'])
        else:
            if is_short:
                self.spin_interval.set_value(parent_config.get('short_break_interval'))
            else:
                self.spin_interval.set_value(parent_config.get('long_break_interval'))

        if duration_overriden:
            self.spin_duration.set_value(break_config['duration'])
        else:
            if is_short:
                self.spin_duration.set_value(parent_config.get('short_break_duration'))
            else:
                self.spin_duration.set_value(parent_config.get('long_break_duration'))
        row = 0
        col = 0
        for plugin_id in plugin_map.keys():
            chk_button = Gtk.CheckButton(_(plugin_map[plugin_id]))
            self.plugin_check_buttons[plugin_id] = chk_button
            grid_plugins.attach(chk_button, row, col, 1, 1)
            if plugins_overriden:
                chk_button.set_active(plugin_id in break_config['plugins'])
            else:
                chk_button.set_active(True)
            row += 1
            if row > 2:
                col += 1
                row = 0
        # GtkSwitch state-set signal is available only from 3.14
        if Gtk.get_minor_version() >= 14:
            self.switch_override_interval.connect('state-set', self.on_switch_override_interval_activate)
            self.switch_override_duration.connect('state-set', self.on_switch_override_duration_activate)
            self.switch_override_plugins.connect('state-set', self.on_switch_override_plugins_activate)
            self.on_switch_override_interval_activate(self.switch_override_interval, self.switch_override_interval.get_active())
            self.on_switch_override_duration_activate(self.switch_override_duration, self.switch_override_duration.get_active())
            self.on_switch_override_plugins_activate(self.switch_override_plugins, self.switch_override_plugins.get_active())

    def on_switch_override_interval_activate(self, switch_button, state):
        """
        switch_override_interval state change event handler.
        """
        self.spin_interval.set_sensitive(state)

    def on_switch_override_duration_activate(self, switch_button, state):
        """
        switch_override_duration state change event handler.
        """
        self.spin_duration.set_sensitive(state)

    def on_switch_override_plugins_activate(self, switch_button, state):
        """
        switch_override_plugins state change event handler.
        """
        for chk_box in self.plugin_check_buttons.values():
            chk_box.set_sensitive(state)

    def select_image(self, button):
        """
        Show a file chooser dialog and let the user to select an image.
        """
        dialog = Gtk.FileChooserDialog(_('Please select an image'), self.window, Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        png_filter = Gtk.FileFilter()
        png_filter.set_name("PNG files")
        png_filter.add_mime_type("image/png")
        png_filter.add_pattern("*.png")
        dialog.add_filter(png_filter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.break_config['image'] = dialog.get_filename()
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.break_config['image'], 16, 16, True)
            self.img_break.set_from_pixbuf(pixbuf)
        elif response == Gtk.ResponseType.CANCEL:
            self.break_config.pop('image', None)
            self.img_break.set_from_stock('gtk-missing-image', Gtk.IconSize.BUTTON)

        dialog.destroy()

    def on_window_delete(self, *args):
        """
        Event handler for Properties dialog close action.
        """
        break_name = self.txt_break.get_text().strip()
        if break_name:
            self.break_config['name'] = break_name
        if self.switch_override_interval.get_active():
            self.break_config['interval'] = int(self.spin_interval.get_value())
        else:
            self.break_config.pop('interval', None)
        if self.switch_override_duration.get_active():
            self.break_config['duration'] = int(self.spin_duration.get_value())
        else:
            self.break_config.pop('duration', None)
        if self.switch_override_plugins.get_active():
            selected_plugins = []
            for plugin_id in self.plugin_check_buttons:
                if self.plugin_check_buttons[plugin_id].get_active():
                    selected_plugins.append(plugin_id)
            self.break_config['plugins'] = selected_plugins
        else:
            self.break_config.pop('plugins', None)

        if self.is_short and self.cmb_type.get_active() == 1:
            # Changed from short to long
            self.parent_config.get('short_breaks').remove(self.break_config)
            self.parent_config.get('long_breaks').append(self.break_config)
            self.on_remove()
            self.on_add(not self.is_short, self.break_config)
        elif not self.is_short and self.cmb_type.get_active() == 0:
            # Changed from long to short
            self.parent_config.get('long_breaks').remove(self.break_config)
            self.parent_config.get('short_breaks').append(self.break_config)
            self.on_remove()
            self.on_add(not self.is_short, self.break_config)
        else:
            self.on_close(self.break_config)
        self.window.destroy()

    def show(self):
        """
        Show the Properties dialog.
        """
        self.window.show_all()


class NewBreakDialog:
    """
    Builds a new break dialog.
    """

    def __init__(self, parent_config, on_add):
        self.parent_config = parent_config
        self.on_add = on_add

        builder = utility.create_gtk_builder(SETTINGS_DIALOG_NEW_BREAK_GLADE)
        builder.connect_signals(self)
        self.window = builder.get_object('dialog_new_break')
        self.txt_break = builder.get_object('txt_break')
        self.cmb_type = builder.get_object('cmb_type')
        list_types = builder.get_object('lst_break_types')

        list_types[0][0] = _(list_types[0][0])
        list_types[1][0] = _(list_types[1][0])

        # Set the values
        self.window.set_title(_('New Break'))

    def discard(self, button):
        """
        Close the dialog.
        """
        self.window.destroy()

    def save(self, button):
        """
        Event handler for Properties dialog close action.
        """
        break_config = {'name': self.txt_break.get_text().strip()}

        if self.cmb_type.get_active() == 0:
            self.parent_config.get('short_breaks').append(break_config)
            self.on_add(True, break_config)
        else:
            self.parent_config.get('long_breaks').append(break_config)
            self.on_add(False, break_config)
        self.window.destroy()

    def on_window_delete(self, *args):
        """
        Event handler for dialog close action.
        """
        self.window.destroy()

    def show(self):
        """
        Show the Properties dialog.
        """
        self.window.show_all()
