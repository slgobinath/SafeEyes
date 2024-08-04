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
from safeeyes.model import Config, PluginDependency
from safeeyes.translations import translate as _

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio
from gi.repository import GdkPixbuf


SETTINGS_DIALOG_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/settings_dialog.glade"
)
SETTINGS_DIALOG_PLUGIN_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/settings_plugin.glade"
)
SETTINGS_DIALOG_BREAK_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/settings_break.glade"
)
SETTINGS_DIALOG_NEW_BREAK_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/new_break.glade"
)
SETTINGS_BREAK_ITEM_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/item_break.glade"
)
SETTINGS_PLUGIN_ITEM_GLADE = os.path.join(
    utility.BIN_DIRECTORY, "glade/item_plugin.glade"
)
SETTINGS_ITEM_INT_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_int.glade")
SETTINGS_ITEM_TEXT_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_text.glade")
SETTINGS_ITEM_BOOL_GLADE = os.path.join(utility.BIN_DIRECTORY, "glade/item_bool.glade")


@Gtk.Template(filename=SETTINGS_DIALOG_GLADE)
class SettingsDialog(Gtk.ApplicationWindow):
    """Create and initialize SettingsDialog instance."""

    __gtype_name__ = "SettingsDialog"

    box_short_breaks = Gtk.Template.Child()
    box_long_breaks = Gtk.Template.Child()
    box_plugins = Gtk.Template.Child()
    popover = Gtk.Template.Child()

    spin_short_break_duration = Gtk.Template.Child()
    spin_long_break_duration = Gtk.Template.Child()
    spin_short_break_interval = Gtk.Template.Child()
    spin_long_break_interval = Gtk.Template.Child()
    spin_time_to_prepare = Gtk.Template.Child()
    spin_postpone_duration = Gtk.Template.Child()
    dropdown_postpone_unit = Gtk.Template.Child()
    spin_disable_keyboard_shortcut = Gtk.Template.Child()
    switch_strict_break = Gtk.Template.Child()
    switch_random_order = Gtk.Template.Child()
    switch_postpone = Gtk.Template.Child()
    switch_persist = Gtk.Template.Child()
    info_bar_long_break = Gtk.Template.Child()

    def __init__(self, application, config, on_save_settings):
        super().__init__(application=application)

        self.config = config
        self.on_save_settings = on_save_settings
        self.plugin_items = {}
        self.plugin_map = {}
        self.last_short_break_interval = config.get("short_break_interval")
        self.initializing = True
        self.infobar_long_break_shown = False

        self.info_bar_long_break.hide()

        # Set the current values of input fields
        self.__initialize(config)

        self.initializing = False

    def __initialize(self, config):
        # Don't show infobar for changes made internally
        self.infobar_long_break_shown = True
        for short_break in config.get("short_breaks"):
            self.__create_break_item(short_break, True)
        for long_break in config.get("long_breaks"):
            self.__create_break_item(long_break, False)

        for plugin_config in utility.load_plugins_config(config):
            self.box_plugins.append(self.__create_plugin_item(plugin_config))

        self.spin_short_break_duration.set_value(config.get("short_break_duration"))
        self.spin_long_break_duration.set_value(config.get("long_break_duration"))
        self.spin_short_break_interval.set_value(config.get("short_break_interval"))
        self.spin_long_break_interval.set_value(config.get("long_break_interval"))
        self.spin_time_to_prepare.set_value(config.get("pre_break_warning_time"))
        self.spin_postpone_duration.set_value(config.get("postpone_duration"))
        # Set the active item in the dropdown based on the postpone unit
        if config.get("postpone_unit") == "seconds":
            self.dropdown_postpone_unit.set_selected(1)
        else:
            self.dropdown_postpone_unit.set_selected(0)
        self.spin_disable_keyboard_shortcut.set_value(
            config.get("shortcut_disable_time")
        )
        self.switch_strict_break.set_active(config.get("strict_break"))
        self.switch_random_order.set_active(config.get("random_order"))
        self.switch_postpone.set_active(config.get("allow_postpone"))
        self.switch_persist.set_active(config.get("persist_state"))
        self.infobar_long_break_shown = False

    def __create_break_item(self, break_config, is_short):
        """Create an entry for break to be listed in the break tab."""
        parent_box = self.box_long_breaks
        if is_short:
            parent_box = self.box_short_breaks

        box = BreakItem(
            break_name=break_config["name"],
            on_properties=lambda: self.__show_break_properties_dialog(
                break_config,
                is_short,
                self.config,
                lambda cfg: box.set_break_name(cfg["name"]),
                lambda is_short, break_config: self.__create_break_item(
                    break_config, is_short
                ),
                lambda: parent_box.remove(box),
            ),
            on_delete=lambda: self.__delete_break(
                break_config,
                is_short,
                lambda: parent_box.remove(box),
            ),
        )

        gbox = box.box

        gbox.set_visible(True)
        parent_box.append(gbox)

    @Gtk.Template.Callback()
    def on_reset_menu_clicked(self, button):
        self.popover.hide()

        def __confirmation_dialog_response(dialog, result) -> None:
            response_id = dialog.choose_finish(result)
            if response_id == 1:
                utility.reset_config()
                self.config = Config.load()
                # Remove breaks from the container
                self.__clear_children(self.box_short_breaks)
                self.__clear_children(self.box_long_breaks)
                self.__clear_children(self.box_plugins)
                # Initialize again
                self.__initialize(self.config)

        messagedialog = Gtk.AlertDialog()
        messagedialog.set_modal(True)
        messagedialog.set_buttons(["_Cancel", _("Reset")])
        messagedialog.set_message(
            _("Are you sure you want to reset all settings to default?")
        )
        messagedialog.set_detail(_("You can't undo this action."))

        messagedialog.set_cancel_button(0)
        messagedialog.set_default_button(0)

        messagedialog.choose(self, None, __confirmation_dialog_response)

    def __clear_children(self, widget):
        while widget.get_last_child() is not None:
            widget.remove(widget.get_last_child())

    def __delete_break(self, break_config, is_short, on_remove):
        """Remove the break after a confirmation."""

        def __confirmation_dialog_response(dialog, result):
            response_id = dialog.choose_finish(result)
            if response_id == 1:
                if is_short:
                    self.config.get("short_breaks").remove(break_config)
                else:
                    self.config.get("long_breaks").remove(break_config)
                on_remove()

        messagedialog = Gtk.AlertDialog()
        messagedialog.set_modal(True)
        messagedialog.set_buttons(["_Cancel", _("Delete")])
        messagedialog.set_message(_("Are you sure you want to delete this break?"))
        messagedialog.set_detail(_("You can't undo this action."))

        messagedialog.set_cancel_button(0)
        messagedialog.set_default_button(0)

        messagedialog.choose(self, None, __confirmation_dialog_response)

    def __create_plugin_item(self, plugin_config):
        """Create an entry for plugin to be listed in the plugin tab."""
        box = PluginItem(
            plugin_config,
            on_properties=lambda: self.__show_plugins_properties_dialog(plugin_config),
        )

        self.plugin_items[plugin_config["id"]] = box

        if plugin_config.get("break_override_allowed", False):
            self.plugin_map[plugin_config["id"]] = plugin_config["meta"]["name"]

        gbox = box.box

        gbox.set_visible(True)
        return gbox

    def __show_plugins_properties_dialog(self, plugin_config):
        """Show the PluginProperties dialog."""
        dialog = PluginSettingsDialog(self, plugin_config)
        dialog.show()

    def __show_break_properties_dialog(
        self, break_config, is_short, parent, on_close, on_add, on_remove
    ):
        """Show the BreakProperties dialog."""
        dialog = BreakSettingsDialog(
            self,
            break_config,
            is_short,
            parent,
            self.plugin_map,
            on_close,
            on_add,
            on_remove,
        )
        dialog.show()

    def show(self):
        """Show the SettingsDialog."""
        super().show()

    @Gtk.Template.Callback()
    def on_switch_postpone_activate(self, switch, state):
        """Event handler to the state change of the postpone switch.

        Enable or disable the self.spin_postpone_duration based on the
        state of the postpone switch.
        """
        self.spin_postpone_duration.set_sensitive(self.switch_postpone.get_active())
        self.dropdown_postpone_unit.set_sensitive(self.switch_postpone.get_active())

    @Gtk.Template.Callback()
    def on_spin_short_break_interval_change(self, spin_button, *value):
        """Event handler for value change of short break interval."""
        short_break_interval = self.spin_short_break_interval.get_value_as_int()
        long_break_interval = self.spin_long_break_interval.get_value_as_int()
        self.spin_long_break_interval.set_range(short_break_interval * 2, 120)
        self.spin_long_break_interval.set_increments(
            short_break_interval, short_break_interval * 2
        )
        self.spin_long_break_interval.set_value(
            short_break_interval
            * math.ceil(long_break_interval / self.last_short_break_interval)
        )
        self.last_short_break_interval = short_break_interval
        if not self.initializing and not self.infobar_long_break_shown:
            self.infobar_long_break_shown = True
            self.info_bar_long_break.show()

    @Gtk.Template.Callback()
    def on_spin_long_break_interval_change(self, spin_button, *value):
        """Event handler for value change of long break interval."""
        if not self.initializing and not self.infobar_long_break_shown:
            self.infobar_long_break_shown = True
            self.info_bar_long_break.show()

    @Gtk.Template.Callback()
    def on_info_bar_long_break_close(self, infobar, *user_data):
        """Event handler for info bar close action."""
        self.info_bar_long_break.hide()

    @Gtk.Template.Callback()
    def add_break(self, button) -> None:
        """Event handler for add break button."""
        dialog = NewBreakDialog(
            self,
            self.config,
            lambda is_short, break_config: self.__create_break_item(
                break_config, is_short
            ),
        )
        dialog.show()

    @Gtk.Template.Callback()
    def on_window_delete(self, *args):
        """Event handler for Settings dialog close action."""
        self.config.set(
            "short_break_duration", self.spin_short_break_duration.get_value_as_int()
        )
        self.config.set(
            "long_break_duration", self.spin_long_break_duration.get_value_as_int()
        )
        self.config.set(
            "short_break_interval", self.spin_short_break_interval.get_value_as_int()
        )
        self.config.set(
            "long_break_interval", self.spin_long_break_interval.get_value_as_int()
        )
        self.config.set(
            "pre_break_warning_time", self.spin_time_to_prepare.get_value_as_int()
        )
        self.config.set(
            "postpone_duration", self.spin_postpone_duration.get_value_as_int()
        )
        self.config.set(
            "postpone_unit",
            self.dropdown_postpone_unit.get_selected_item().get_string(),
        )
        self.config.set(
            "shortcut_disable_time",
            self.spin_disable_keyboard_shortcut.get_value_as_int(),
        )
        self.config.set("strict_break", self.switch_strict_break.get_active())
        self.config.set("random_order", self.switch_random_order.get_active())
        self.config.set("allow_postpone", self.switch_postpone.get_active())
        self.config.set("persist_state", self.switch_persist.get_active())
        for plugin in self.config.get("plugins"):
            if plugin["id"] in self.plugin_items:
                plugin["enabled"] = self.plugin_items[plugin["id"]].is_enabled()

        self.on_save_settings(self.config)  # Call the provided save method
        self.destroy()


class BreakItem:
    def __init__(self, break_name, on_properties, on_delete):
        super().__init__()

        self.on_properties = on_properties
        self.on_delete = on_delete

        builder = utility.create_gtk_builder(SETTINGS_BREAK_ITEM_GLADE)
        self.box = builder.get_object("box")
        self.lbl_name = builder.get_object("lbl_name")
        self.lbl_name.set_label(_(break_name))
        self.btn_properties = builder.get_object("btn_properties")
        self.btn_properties.connect("clicked", self.on_properties_clicked)
        self.btn_delete = builder.get_object("btn_delete")
        self.btn_delete.connect("clicked", self.on_delete_clicked)

    def set_break_name(self, break_name):
        self.lbl_name.set_label(_(break_name))

    def on_properties_clicked(self, button):
        self.on_properties()

    def on_delete_clicked(self, button):
        self.on_delete()


class PluginItem:
    def __init__(self, plugin_config, on_properties):
        super().__init__()

        self.on_properties = on_properties
        self.plugin_config = plugin_config

        builder = utility.create_gtk_builder(SETTINGS_PLUGIN_ITEM_GLADE)
        self.lbl_plugin_name = builder.get_object("lbl_plugin_name")
        self.lbl_plugin_description = builder.get_object("lbl_plugin_description")
        self.switch_enable = builder.get_object("switch_enable")
        self.btn_properties = builder.get_object("btn_properties")
        self.lbl_plugin_name.set_label(_(plugin_config["meta"]["name"]))
        self.switch_enable.set_active(plugin_config["enabled"])

        if plugin_config["error"]:
            message = plugin_config["meta"]["dependency_description"]
            if isinstance(message, PluginDependency):
                self.lbl_plugin_description.set_label(_(message.message))
                self.btn_plugin_extra_link = builder.get_object("btn_plugin_extra_link")
                self.btn_plugin_extra_link.set_uri(message.link)
                self.btn_plugin_extra_link.set_visible(True)
            else:
                self.lbl_plugin_description.set_label(_(message))
            self.lbl_plugin_name.set_sensitive(False)
            self.lbl_plugin_description.set_sensitive(False)
            self.switch_enable.set_sensitive(False)
            self.btn_properties.set_sensitive(False)
            if plugin_config["enabled"]:
                self.btn_disable_errored = builder.get_object("btn_disable_errored")
                self.btn_disable_errored.set_visible(True)
                self.btn_disable_errored.connect("clicked", self.on_disable_errored)
        else:
            self.lbl_plugin_description.set_label(
                _(plugin_config["meta"]["description"])
            )
            if plugin_config["settings"]:
                self.btn_properties.set_sensitive(True)
                self.btn_properties.connect("clicked", self.on_properties_clicked)
            else:
                self.btn_properties.set_sensitive(False)

        if plugin_config["icon"]:
            builder.get_object("img_plugin_icon").set_from_file(plugin_config["icon"])

        self.box = builder.get_object("box")

    def is_enabled(self):
        return self.switch_enable.get_active()

    def on_disable_errored(self, button):
        """Permanently disable errored plugin."""
        self.btn_disable_errored.set_sensitive(False)
        self.switch_enable.set_active(False)

    def on_properties_clicked(self, button):
        if not self.plugin_config["error"] and self.plugin_config["settings"]:
            self.on_properties()


class IntItem:
    def __init__(self, name, value, min_value, max_value):
        super().__init__()

        builder = utility.create_gtk_builder(SETTINGS_ITEM_INT_GLADE)
        builder.get_object("lbl_name").set_label(_(name))
        self.spin_value = builder.get_object("spin_value")
        self.spin_value.set_range(min_value, max_value)
        self.spin_value.set_value(value)
        self.box = builder.get_object("box")

    def get_value(self):
        return self.spin_value.get_value()


class TextItem:
    def __init__(self, name, value):
        super().__init__()

        builder = utility.create_gtk_builder(SETTINGS_ITEM_TEXT_GLADE)
        builder.get_object("lbl_name").set_label(_(name))
        self.txt_value = builder.get_object("txt_value")
        self.txt_value.set_text(value)
        self.box = builder.get_object("box")

    def get_value(self):
        return self.txt_value.get_text()


class BoolItem:
    def __init__(self, name, value):
        super().__init__()

        builder = utility.create_gtk_builder(SETTINGS_ITEM_BOOL_GLADE)
        builder.get_object("lbl_name").set_label(_(name))
        self.switch_value = builder.get_object("switch_value")
        self.switch_value.set_active(value)
        self.box = builder.get_object("box")

    def get_value(self):
        return self.switch_value.get_active()


class PluginSettingsDialog:
    """Builds a settings dialog based on the configuration of a plugin."""

    def __init__(self, parent, config):
        self.config = config
        self.property_controls = []

        builder = utility.create_gtk_builder(SETTINGS_DIALOG_PLUGIN_GLADE)
        self.window = builder.get_object("dialog_settings_plugin")
        self.window.set_transient_for(parent)
        box_settings = builder.get_object("box_settings")
        self.window.set_title(_("Plugin Settings"))
        for setting in config.get("settings"):
            if setting["type"].upper() == "INT":
                box = IntItem(
                    setting["label"],
                    config["active_plugin_config"][setting["id"]],
                    setting.get("min", 0),
                    setting.get("max", 120),
                )
            elif setting["type"].upper() == "TEXT":
                box = TextItem(
                    setting["label"], config["active_plugin_config"][setting["id"]]
                )
            elif setting["type"].upper() == "BOOL":
                box = BoolItem(
                    setting["label"], config["active_plugin_config"][setting["id"]]
                )
            else:
                continue

            self.property_controls.append({"key": setting["id"], "box": box})
            box_settings.append(box.box)

        self.window.connect("close-request", self.on_window_delete)

    def on_window_delete(self, *args):
        """Event handler for Properties dialog close action."""
        for property_control in self.property_controls:
            self.config["active_plugin_config"][property_control["key"]] = (
                property_control["box"].get_value()
            )
        self.window.destroy()

    def show(self):
        """Show the Properties dialog."""
        self.window.present()


class BreakSettingsDialog:
    """Builds a settings dialog based on the configuration of a plugin."""

    def __init__(
        self,
        parent,
        break_config,
        is_short,
        parent_config,
        plugin_map,
        on_close,
        on_add,
        on_remove,
    ):
        self.break_config = break_config
        self.parent_config = parent_config
        self.plugin_check_buttons = {}
        self.on_close = on_close
        self.is_short = is_short
        self.on_add = on_add
        self.on_remove = on_remove

        builder = utility.create_gtk_builder(SETTINGS_DIALOG_BREAK_GLADE)
        self.window = builder.get_object("dialog_settings_break")
        self.window.set_transient_for(parent)
        self.txt_break = builder.get_object("txt_break")
        self.switch_override_interval = builder.get_object("switch_override_interval")
        self.switch_override_duration = builder.get_object("switch_override_duration")
        self.switch_override_plugins = builder.get_object("switch_override_plugins")
        self.spin_interval = builder.get_object("spin_interval")
        self.spin_duration = builder.get_object("spin_duration")
        self.btn_image = builder.get_object("btn_image")
        self.cmb_type = builder.get_object("cmb_type")

        grid_plugins = builder.get_object("grid_plugins")
        list_types = builder.get_object("lst_break_types")

        interval_overriden = break_config.get("interval", None) is not None
        duration_overriden = break_config.get("duration", None) is not None
        plugins_overriden = break_config.get("plugins", None) is not None

        # Set the values
        self.window.set_title(_("Break Settings"))
        self.txt_break.set_text(_(break_config["name"]))
        self.switch_override_interval.set_active(interval_overriden)
        self.switch_override_duration.set_active(duration_overriden)
        self.switch_override_plugins.set_active(plugins_overriden)
        self.cmb_type.set_active(0 if is_short else 1)
        list_types[0][0] = _(list_types[0][0])
        list_types[1][0] = _(list_types[1][0])

        if interval_overriden:
            self.spin_interval.set_value(break_config["interval"])
        else:
            if is_short:
                self.spin_interval.set_value(parent_config.get("short_break_interval"))
            else:
                self.spin_interval.set_value(parent_config.get("long_break_interval"))

        if duration_overriden:
            self.spin_duration.set_value(break_config["duration"])
        else:
            if is_short:
                self.spin_duration.set_value(parent_config.get("short_break_duration"))
            else:
                self.spin_duration.set_value(parent_config.get("long_break_duration"))
        row = 0
        col = 0
        for plugin_id in plugin_map.keys():
            chk_button = Gtk.CheckButton.new_with_label(_(plugin_map[plugin_id]))
            self.plugin_check_buttons[plugin_id] = chk_button
            grid_plugins.attach(chk_button, row, col, 1, 1)
            if plugins_overriden:
                chk_button.set_active(plugin_id in break_config["plugins"])
            else:
                chk_button.set_active(True)
            row += 1
            if row > 2:
                col += 1
                row = 0

        if "image" in self.break_config:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                self.break_config["image"], 16, 16, True
            )
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            self.btn_image.set_child(image)

        self.window.connect("close-request", self.on_window_delete)
        self.btn_image.connect("clicked", self.select_image)

        self.switch_override_interval.connect(
            "state-set", self.on_switch_override_interval_activate
        )
        self.switch_override_duration.connect(
            "state-set", self.on_switch_override_duration_activate
        )
        self.switch_override_plugins.connect(
            "state-set", self.on_switch_override_plugins_activate
        )
        self.on_switch_override_interval_activate(
            self.switch_override_interval, self.switch_override_interval.get_active()
        )
        self.on_switch_override_duration_activate(
            self.switch_override_duration, self.switch_override_duration.get_active()
        )
        self.on_switch_override_plugins_activate(
            self.switch_override_plugins, self.switch_override_plugins.get_active()
        )

    def on_switch_override_interval_activate(self, switch_button, state):
        """switch_override_interval state change event handler."""
        self.spin_interval.set_sensitive(state)

    def on_switch_override_duration_activate(self, switch_button, state):
        """switch_override_duration state change event handler."""
        self.spin_duration.set_sensitive(state)

    def on_switch_override_plugins_activate(self, switch_button, state):
        """switch_override_plugins state change event handler."""
        for chk_box in self.plugin_check_buttons.values():
            chk_box.set_sensitive(state)

    def select_image(self, button):
        """Show a file chooser dialog and let the user to select an image."""
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Please select an image"))

        png_filter = Gtk.FileFilter()
        png_filter.set_name("PNG files")
        png_filter.add_mime_type("image/png")
        png_filter.add_pattern("*.png")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(png_filter)
        dialog.set_filters(filters)

        dialog.open(self.window, None, self.select_image_callback)

    def select_image_callback(self, dialog, result):
        response = None

        try:
            response = dialog.open_finish(result)
        except Exception:
            # user pressing "Cancel" throws a generic exception here
            pass

        if response is not None:
            self.break_config["image"] = response.get_path()
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                self.break_config["image"], 16, 16, True
            )
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            self.btn_image.set_child(image)
        else:
            self.break_config.pop("image", None)
            self.btn_image.set_icon_name("gtk-missing-image")

    def on_window_delete(self, *args):
        """Event handler for Properties dialog close action."""
        break_name = self.txt_break.get_text().strip()
        if break_name:
            self.break_config["name"] = break_name
        if self.switch_override_interval.get_active():
            self.break_config["interval"] = int(self.spin_interval.get_value())
        else:
            self.break_config.pop("interval", None)
        if self.switch_override_duration.get_active():
            self.break_config["duration"] = int(self.spin_duration.get_value())
        else:
            self.break_config.pop("duration", None)
        if self.switch_override_plugins.get_active():
            selected_plugins = []
            for plugin_id in self.plugin_check_buttons:
                if self.plugin_check_buttons[plugin_id].get_active():
                    selected_plugins.append(plugin_id)
            self.break_config["plugins"] = selected_plugins
        else:
            self.break_config.pop("plugins", None)

        if self.is_short and self.cmb_type.get_active() == 1:
            # Changed from short to long
            self.parent_config.get("short_breaks").remove(self.break_config)
            self.parent_config.get("long_breaks").append(self.break_config)
            self.on_remove()
            self.on_add(not self.is_short, self.break_config)
        elif not self.is_short and self.cmb_type.get_active() == 0:
            # Changed from long to short
            self.parent_config.get("long_breaks").remove(self.break_config)
            self.parent_config.get("short_breaks").append(self.break_config)
            self.on_remove()
            self.on_add(not self.is_short, self.break_config)
        else:
            self.on_close(self.break_config)
        self.window.destroy()

    def show(self):
        """Show the Properties dialog."""
        self.window.present()


class NewBreakDialog:
    """Builds a new break dialog."""

    def __init__(self, parent, parent_config, on_add):
        self.parent_config = parent_config
        self.on_add = on_add

        builder = utility.create_gtk_builder(SETTINGS_DIALOG_NEW_BREAK_GLADE)
        self.window = builder.get_object("dialog_new_break")
        self.window.set_transient_for(parent)
        self.txt_break = builder.get_object("txt_break")
        self.cmb_type = builder.get_object("cmb_type")
        list_types = builder.get_object("lst_break_types")

        list_types[0][0] = _(list_types[0][0])
        list_types[1][0] = _(list_types[1][0])

        self.window.connect("close-request", self.on_window_delete)
        builder.get_object("btn_discard").connect("clicked", self.discard)
        builder.get_object("btn_save").connect("clicked", self.save)

        # Set the values
        self.window.set_title(_("New Break"))

    def discard(self, button):
        """Close the dialog."""
        self.window.destroy()

    def save(self, button):
        """Event handler for Properties dialog close action."""
        break_config = {"name": self.txt_break.get_text().strip()}

        if self.cmb_type.get_active() == 0:
            self.parent_config.get("short_breaks").append(break_config)
            self.on_add(True, break_config)
        else:
            self.parent_config.get("long_breaks").append(break_config)
            self.on_add(False, break_config)
        self.window.destroy()

    def on_window_delete(self, *args):
        """Event handler for dialog close action."""
        self.window.destroy()

    def show(self):
        """Show the Properties dialog."""
        self.window.present()
