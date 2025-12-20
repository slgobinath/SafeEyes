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

import datetime
from safeeyes.model import BreakType
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib
import logging
from safeeyes import utility
from safeeyes.context import Context
from safeeyes.translations import translate as _
import typing

"""
Safe Eyes tray icon plugin
"""

tray_icon: typing.Optional["TrayIcon"] = None
safeeyes_config = None

SNI_NODE_INFO = Gio.DBusNodeInfo.new_for_xml(
    """
<?xml version="1.0" encoding="UTF-8"?>
<node>
    <interface name="org.kde.StatusNotifierItem">
        <property name="Category" type="s" access="read"/>
        <property name="Id" type="s" access="read"/>
        <property name="Title" type="s" access="read"/>
        <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
        <property name="Menu" type="o" access="read"/>
        <property name="ItemIsMenu" type="b" access="read"/>
        <property name="IconName" type="s" access="read"/>
        <property name="IconThemePath" type="s" access="read"/>
        <property name="Status" type="s" access="read"/>
        <signal name="NewIcon"/>
        <signal name="NewTooltip"/>

        <method name="ProvideXdgActivationToken">
            <arg name="token" type="s" direction="in"/>
        </method>

        <property name="XAyatanaLabel" type="s" access="read"/>
        <signal name="XAyatanaNewLabel">
            <arg type="s" name="label" direction="out" />
            <arg type="s" name="guide" direction="out" />
        </signal>
    </interface>
</node>"""
).interfaces[0]

MENU_NODE_INFO = Gio.DBusNodeInfo.new_for_xml(
    """
<?xml version="1.0" encoding="UTF-8"?>
<node>
    <interface name="com.canonical.dbusmenu">
        <method name="GetLayout">
            <arg type="i" direction="in"/>
            <arg type="i" direction="in"/>
            <arg type="as" direction="in"/>
            <arg type="u" direction="out"/>
            <arg type="(ia{sv}av)" direction="out"/>
        </method>
        <method name="GetGroupProperties">
            <arg type="ai" name="ids" direction="in"/>
            <arg type="as" name="propertyNames" direction="in" />
            <arg type="a(ia{sv})" name="properties" direction="out" />
        </method>
        <method name="GetProperty">
            <arg type="i" name="id" direction="in"/>
            <arg type="s" name="name" direction="in"/>
            <arg type="v" name="value" direction="out"/>
        </method>
        <method name="Event">
            <arg type="i" direction="in"/>
            <arg type="s" direction="in"/>
            <arg type="v" direction="in"/>
            <arg type="u" direction="in"/>
        </method>
        <method name="EventGroup">
            <arg type="a(isvu)" name="events" direction="in" />
            <arg type="ai" name="idErrors" direction="out" />
        </method>
        <method name="AboutToShow">
            <arg type="i" direction="in"/>
            <arg type="b" direction="out"/>
        </method>
        <method name="AboutToShowGroup">
            <arg type="ai" name="ids" direction="in" />
            <arg type="ai" name="updatesNeeded" direction="out" />
            <arg type="ai" name="idErrors" direction="out" />
        </method>
        <signal name="LayoutUpdated">
            <arg type="u"/>
            <arg type="i"/>
        </signal>
    </interface>
</node>"""
).interfaces[0]


class DBusService:
    def __init__(self, interface_info, object_path, bus):
        self.interface_info = interface_info
        self.bus = bus
        self.object_path = object_path
        self.registration_id = None

    def register(self):
        self.registration_id = self.bus.register_object(
            object_path=self.object_path,
            interface_info=self.interface_info,
            method_call_closure=self.on_method_call,
            get_property_closure=self.on_get_property,
        )

        if not self.registration_id:
            raise GLib.Error(f"Failed to register object with path {self.object_path}")

        self.interface_info.cache_build()

    def unregister(self):
        self.interface_info.cache_release()

        if self.registration_id is not None:
            self.bus.unregister_object(self.registration_id)
            self.registration_id = None

    def on_method_call(
        self,
        _connection,
        _sender,
        _path,
        _interface_name,
        method_name,
        parameters,
        invocation,
    ):
        method_info = self.interface_info.lookup_method(method_name)
        method = getattr(self, method_name)
        result = method(*parameters.unpack())
        out_arg_types = "".join([arg.signature for arg in method_info.out_args])
        return_value = None

        if method_info.out_args:
            return_value = GLib.Variant(f"({out_arg_types})", result)

        invocation.return_value(return_value)

    def on_get_property(
        self, _connection, _sender, _path, _interface_name, property_name
    ):
        property_info = self.interface_info.lookup_property(property_name)
        return GLib.Variant(property_info.signature, getattr(self, property_name))

    def emit_signal(self, signal_name, args=None):
        signal_info = self.interface_info.lookup_signal(signal_name)
        if len(signal_info.args) == 0:
            parameters = None
        else:
            arg_types = "".join([arg.signature for arg in signal_info.args])
            parameters = GLib.Variant(f"({arg_types})", args)
        self.bus.emit_signal(
            destination_bus_name=None,
            object_path=self.object_path,
            interface_name=self.interface_info.name,
            signal_name=signal_name,
            parameters=parameters,
        )


class DBusMenuService(DBusService):
    DBUS_SERVICE_PATH = "/io/github/slgobinath/SafeEyes/Menu"

    revision = 0

    # TODO: replace dict here with more exact typing for item
    items: list[dict] = []
    # TODO: replace dict here with more exact typing for item
    idToItems: dict[str, dict] = {}

    def __init__(self, session_bus, items):
        super().__init__(
            interface_info=MENU_NODE_INFO,
            object_path=self.DBUS_SERVICE_PATH,
            bus=session_bus,
        )

        self.set_items(items)

    def set_items(self, items):
        self.items = items

        self.idToItems = self.getItemsFlat(items, {})

        self.revision += 1

        self.LayoutUpdated(self.revision, 0)

    @staticmethod
    def getItemsFlat(items, idToItems):
        for item in items:
            if item.get("hidden", False):
                continue

            idToItems[item["id"]] = item

            if "children" in item:
                idToItems = DBusMenuService.getItemsFlat(item["children"], idToItems)

        return idToItems

    @staticmethod
    def singleItemToDbus(item):
        props = DBusMenuService.itemPropsToDbus(item)

        return (item["id"], props)

    @staticmethod
    def itemPropsToDbus(item):
        result = {}

        string_props = ["label", "icon-name", "type", "children-display"]
        for key in string_props:
            if key in item:
                result[key] = GLib.Variant("s", item[key])

        bool_props = ["enabled"]
        for key in bool_props:
            if key in item:
                result[key] = GLib.Variant("b", item[key])

        return result

    @staticmethod
    def itemToDbus(item, recursion_depth):
        if item.get("hidden", False):
            return None

        props = DBusMenuService.itemPropsToDbus(item)

        children = []
        if recursion_depth > 1 or recursion_depth == -1:
            if "children" in item:
                children = [
                    DBusMenuService.itemToDbus(item, recursion_depth - 1)
                    for item in item["children"]
                ]
                children = [i for i in children if i is not None]

        return GLib.Variant("(ia{sv}av)", (item["id"], props, children))

    def findItemsWithParent(self, parent_id, items):
        for item in items:
            if item.get("hidden", False):
                continue
            if "children" in item:
                if item["id"] == parent_id:
                    return item["children"]
                else:
                    ret = self.findItemsWithParent(parent_id, item["children"])
                    if ret is not None:
                        return ret
        return None

    def GetLayout(self, parent_id, recursion_depth, property_names):
        children = []

        if parent_id == 0:
            children = self.items
        else:
            children = self.findItemsWithParent(parent_id, self.items)
            if children is None:
                children = []

        children = [self.itemToDbus(item, recursion_depth) for item in children]
        children = [i for i in children if i is not None]

        ret = (
            self.revision,
            (0, {"children-display": GLib.Variant("s", "submenu")}, children),
        )

        return ret

    def GetGroupProperties(self, ids, property_names):
        ret = []

        for idx in ids:
            if idx in self.idToItems:
                props = DBusMenuService.singleItemToDbus(self.idToItems[idx])
                if props is not None:
                    ret.append(props)

        return (ret,)

    def GetProperty(self, idx, name):
        ret = None

        if idx in self.idToItems:
            props = DBusMenuService.singleItemToDbus(self.idToItems[idx])
            if props is not None and name in props:
                ret = props[name]

        return ret

    def Event(self, idx, event_id, data, timestamp):
        if event_id != "clicked":
            return

        if idx in self.idToItems:
            item = self.idToItems[idx]
            if "callback" in item:
                item["callback"]()

    def EventGroup(self, events):
        not_found = []

        for idx, event_id, data, timestamp in events:
            if idx not in self.idToItems:
                not_found.append(idx)
                continue

            if event_id != "clicked":
                continue

            item = self.idToItems[idx]
            if "callback" in item:
                item["callback"]()

        return not_found

    def AboutToShow(self, item_id):
        return (False,)

    def AboutToShowGroup(self, ids):
        not_found = []

        for idx in ids:
            if idx not in self.idToItems:
                not_found.append(idx)
                continue

        return ([], not_found)

    def LayoutUpdated(self, revision, parent):
        self.emit_signal("LayoutUpdated", (revision, parent))


class StatusNotifierItemService(DBusService):
    DBUS_SERVICE_PATH = "/org/ayatana/NotificationItem/io_github_slgobinath_SafeEyes"

    Category = "ApplicationStatus"
    Id = "io.github.slgobinath.SafeEyes"
    Title = "Safe Eyes"
    Status = "Active"
    IconName = "io.github.slgobinath.SafeEyes-enabled"
    IconThemePath = ""
    ToolTip: tuple[str, list[typing.Any], str, str] = ("", [], "Safe Eyes", "")
    XAyatanaLabel = ""
    ItemIsMenu = True
    Menu = None

    last_activation_token: typing.Optional[str] = None

    def __init__(self, session_bus, menu_items):
        super().__init__(
            interface_info=SNI_NODE_INFO,
            object_path=self.DBUS_SERVICE_PATH,
            bus=session_bus,
        )

        self.bus = session_bus

        self._menu = DBusMenuService(session_bus, menu_items)
        self.Menu = self._menu.DBUS_SERVICE_PATH

    def register(self):
        self._menu.register()
        super().register()

        watcher = Gio.DBusProxy.new_sync(
            connection=self.bus,
            flags=Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
            info=None,
            name="org.kde.StatusNotifierWatcher",
            object_path="/StatusNotifierWatcher",
            interface_name="org.kde.StatusNotifierWatcher",
            cancellable=None,
        )

        # Note that according to the (freedesktop) spec, we should own the name
        # org.freedesktop.StatusNotifierItem-PID-ID and pass that to the watcher
        # instead
        # with the path being hardcoded at /StatusNotifierItem
        # The spec behaviour is worse for flatpak, however, as it requires owning a
        # pretty generic name.
        # Note that libappindicator/ayatana also used this non-standard behaviour -
        # this must be pretty well supported then.
        watcher.RegisterStatusNotifierItem("(s)", self.DBUS_SERVICE_PATH)

    def unregister(self):
        super().unregister()
        self._menu.unregister()

    def set_items(self, items):
        self._menu.set_items(items)

    def set_icon(self, icon):
        self.IconName = icon

        self.emit_signal("NewIcon")

    def set_tooltip(self, title, description):
        self.ToolTip = ("", [], title, description)

        self.emit_signal("NewTooltip")

    def set_xayatanalabel(self, label):
        self.XAyatanaLabel = label

        self.emit_signal("XAyatanaNewLabel", (label, ""))

    def ProvideXdgActivationToken(self, token: str) -> None:
        self.last_activation_token = token


class TrayIcon:
    """Create and show the tray icon along with the tray menu."""

    _animation_timeout_id: typing.Optional[int] = None
    _animation_icon_enabled: bool = False

    _resume_timeout_id: typing.Optional[int] = None

    _session_bus: Gio.DBusConnection

    def __init__(self, context: Context, plugin_config):
        self.context = context
        self.on_show_settings = context.api.show_settings
        self.on_show_about = context.api.show_about
        self.quit = context.api.quit
        self.enable_safeeyes = context.api.enable_safeeyes
        self.disable_safeeyes = context.api.disable_safeeyes
        self.take_break = context.api.take_break
        self.has_breaks = context.api.has_breaks
        self.get_break_time = context.api.get_break_time
        self.plugin_config = plugin_config
        self.date_time = None
        self.active = True
        self.wakeup_time = None
        self.allow_disabling = plugin_config["allow_disabling"]
        self.menu_locked = False

        # This is using a separate dbus connection on purpose
        # StatusNotifierWatcher does not have an unregister method - the spec instead
        # says that the watcher should detect the item "going away from the bus"
        # in practice, this means that the connection closing is detected by the watcher
        # which can only happen if we use our own connection, and close it manually
        self._session_bus = Gio.DBusConnection.new_for_address_sync(
            Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION),
            Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT
            | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
        )

        self.sni_service = StatusNotifierItemService(
            self._session_bus, menu_items=self.get_items()
        )
        self.sni_service.register()

        self.update_tooltip()

    def initialize(self, plugin_config):
        """Initialize the tray icon by setting the config."""
        self.plugin_config = plugin_config
        self.allow_disabling = plugin_config["allow_disabling"]

        self.update_menu()
        self.update_tooltip()

    def unregister(self) -> None:
        self.sni_service.unregister()
        self._session_bus.close_sync()

    def get_items(self):
        breaks_found = self.has_breaks()

        info_message = _("No Breaks Available")

        if breaks_found:
            if self.active:
                next_break = self.get_next_break_time()

                if next_break is not None:
                    (next_time, next_long_time, next_is_long) = next_break

                    if next_long_time:
                        if next_is_long:
                            info_message = _("Next long break at %s") % (next_long_time)
                        else:
                            info_message = _("Next breaks at %(short)s/%(long)s") % {
                                "short": next_time,
                                "long": next_long_time,
                            }
                    else:
                        info_message = _("Next break at %s") % (next_time)
            else:
                if self.wakeup_time:
                    info_message = _("Disabled until %s") % utility.format_time(
                        self.wakeup_time
                    )
                else:
                    info_message = _("Disabled until restart")

        disable_items = []

        if self.allow_disabling:
            disable_option_dynamic_id = 13

            for disable_option in self.plugin_config["disable_options"]:
                time_in_minutes = time_in_x = disable_option["time"]

                # Validate time value
                if not isinstance(time_in_minutes, int) or time_in_minutes <= 0:
                    logging.error(
                        "Invalid time in disable option: " + str(time_in_minutes)
                    )
                    continue
                time_unit = disable_option["unit"].lower()
                if time_unit == "seconds" or time_unit == "second":
                    time_in_minutes = int(time_in_minutes / 60)
                    label = self.context["locale"].ngettext(
                        "For %(num)d Second", "For %(num)d Seconds", time_in_x
                    ) % {"num": time_in_x}
                elif time_unit == "minutes" or time_unit == "minute":
                    time_in_minutes = int(time_in_minutes * 1)
                    label = self.context["locale"].ngettext(
                        "For %(num)d Minute", "For %(num)d Minutes", time_in_x
                    ) % {"num": time_in_x}
                elif time_unit == "hours" or time_unit == "hour":
                    time_in_minutes = int(time_in_minutes * 60)
                    label = self.context["locale"].ngettext(
                        "For %(num)d Hour", "For %(num)d Hours", time_in_x
                    ) % {"num": time_in_x}
                else:
                    # Invalid unit
                    logging.error(
                        "Invalid unit in disable option: " + str(disable_option)
                    )
                    continue

                ttw = time_in_minutes
                disable_items.append(
                    {
                        "id": disable_option_dynamic_id,
                        "label": label,
                        "callback": lambda ttw=ttw: self.on_disable_clicked(ttw),
                    }
                )

                disable_option_dynamic_id += 1

            disable_items.append(
                {
                    "id": 12,
                    "label": _("Until restart"),
                    "callback": lambda: self.on_disable_clicked(-1),
                }
            )

        return [
            {
                "id": 1,
                "label": info_message,
                "icon-name": "io.github.slgobinath.SafeEyes-timer",
                "enabled": breaks_found and self.active,
            },
            {
                "id": 2,
                "type": "separator",
            },
            {
                "id": 3,
                "label": _("Enable Safe Eyes"),
                "enabled": breaks_found and not self.active,
                "callback": self.on_enable_clicked,
                "hidden": not self.allow_disabling,
            },
            {
                "id": 4,
                "label": _("Disable Safe Eyes"),
                "enabled": breaks_found and self.active and not self.menu_locked,
                "children-display": "submenu",
                "children": disable_items,
                "hidden": not self.allow_disabling,
            },
            {
                "id": 5,
                "label": _("Take a break now"),
                "enabled": breaks_found and self.active and not self.menu_locked,
                "children-display": "submenu",
                "children": [
                    {
                        "id": 9,
                        "label": _("Any break"),
                        "callback": lambda: self.on_manual_break_clicked(None),
                    },
                    {
                        "id": 10,
                        "label": _("Short break"),
                        "callback": lambda: self.on_manual_break_clicked(
                            BreakType.SHORT_BREAK
                        ),
                    },
                    {
                        "id": 11,
                        "label": _("Long break"),
                        "callback": lambda: self.on_manual_break_clicked(
                            BreakType.LONG_BREAK
                        ),
                    },
                ],
            },
            {
                "id": 6,
                "label": _("Settings"),
                "enabled": not self.menu_locked,
                "callback": self.show_settings,
            },
            {
                "id": 7,
                "label": _("About"),
                "callback": self.show_about,
            },
            {
                "id": 8,
                "label": _("Quit"),
                "enabled": not self.menu_locked,
                "callback": self.quit_safe_eyes,
                "hidden": not self.allow_disabling,
            },
        ]

    def update_menu(self):
        self.sni_service.set_items(self.get_items())

    def update_tooltip(self):
        next_break = self.get_next_break_time()

        if next_break is not None and self.plugin_config.get(
            "show_time_in_tray", False
        ):
            (next_time, next_long_time, _next_is_long) = next_break

            if next_long_time and self.plugin_config.get(
                "show_long_time_in_tray", False
            ):
                description = next_long_time
            else:
                description = next_time
        else:
            description = ""

        self.sni_service.set_tooltip("Safe Eyes", description)
        self.sni_service.set_xayatanalabel(description)

    def quit_safe_eyes(self):
        """Handle Quit menu action.

        This action terminates the application.
        """
        self.active = True
        self.__clear_resume_timer()

        self.quit()

    def show_settings(self) -> None:
        """Handle Settings menu action.

        This action shows the Settings dialog.
        """
        self.on_show_settings(self.sni_service.last_activation_token)

    def show_about(self) -> None:
        """Handle About menu action.

        This action shows the About dialog.
        """
        self.on_show_about(self.sni_service.last_activation_token)

    def next_break_time(self, dateTime):
        """Update the next break time to be displayed in the menu and
        optionally in the tray icon.
        """
        logging.info("Update next break information")
        self.date_time = dateTime
        self.update_menu()
        self.update_tooltip()

    def get_next_break_time(self):
        if not (self.has_breaks() and self.active and self.date_time):
            return None

        formatted_time = utility.format_time(self.get_break_time())
        long_time = self.get_break_time(BreakType.LONG_BREAK)

        if long_time:
            long_time = utility.format_time(long_time)
            if long_time == formatted_time:
                return (long_time, long_time, True)
            else:
                return (formatted_time, long_time, False)

        return (formatted_time, None, False)

    def on_manual_break_clicked(self, break_type):
        """Trigger a break manually."""
        self.take_break(break_type)

    def on_enable_clicked(self):
        """Handle 'Enable Safe Eyes' menu action.

        This action enables the application if it is currently disabled.
        """
        if not self.active:
            self.enable_ui()
            self.enable_safeeyes()
            self.__clear_resume_timer()

    def on_disable_clicked(self, time_to_wait):
        """Handle the menu actions of all the sub menus of 'Disable Safe Eyes'.

        This action disables the application if it is currently active.
        """
        if self.active:
            self.disable_ui()

            if time_to_wait <= 0:
                info = _("Disabled until restart")
                self.disable_safeeyes(info)
                self.wakeup_time = None
            else:
                self.wakeup_time = datetime.datetime.now() + datetime.timedelta(
                    minutes=time_to_wait
                )
                info = _("Disabled until %s") % utility.format_time(self.wakeup_time)
                self.disable_safeeyes(info)
                self._resume_timeout_id = GLib.timeout_add_seconds(
                    time_to_wait * 60, self.__resume
                )
            self.update_menu()

    def lock_menu(self):
        """This method is called by the core to prevent user from disabling
        Safe Eyes after the notification.
        """
        if self.active:
            self.menu_locked = True
            self.update_menu()

    def unlock_menu(self):
        """This method is called by the core to activate the menu after the the
        break.
        """
        if self.active:
            self.menu_locked = False
            self.update_menu()

    def disable_ui(self):
        """Change the UI to disabled state."""
        if self.active:
            logging.info("Disable Safe Eyes")
            self.active = False

            self.sni_service.set_icon("io.github.slgobinath.SafeEyes-disabled")
            self.update_menu()

    def enable_ui(self):
        """Change the UI to enabled state."""
        if not self.active:
            logging.info("Enable Safe Eyes")
            self.active = True

            self.sni_service.set_icon("io.github.slgobinath.SafeEyes-enabled")
            self.update_menu()

    def __resume(self):
        """Reenable Safe Eyes after the given timeout."""
        if not self.active:
            self.on_enable_clicked()

        self._resume_timeout_id = None

        return GLib.SOURCE_REMOVE

    def __clear_resume_timer(self):
        if self._resume_timeout_id is not None:
            GLib.source_remove(self._resume_timeout_id)
            self._resume_timeout_id = None

    def start_animation(self) -> None:
        if self._animation_timeout_id is not None:
            self.stop_animation()

        self._animation_icon_enabled = False

        self._animation_timeout_id = GLib.timeout_add(500, self._do_animate)

    def _do_animate(self) -> bool:
        if not self.active:
            self._animation_timeout_id = None
            return GLib.SOURCE_REMOVE

        if self._animation_icon_enabled:
            self.sni_service.set_icon("io.github.slgobinath.SafeEyes-enabled")
        else:
            self.sni_service.set_icon("io.github.slgobinath.SafeEyes-disabled")

        self._animation_icon_enabled = not self._animation_icon_enabled

        return GLib.SOURCE_CONTINUE

    def stop_animation(self) -> None:
        if self._animation_timeout_id is not None:
            GLib.source_remove(self._animation_timeout_id)
            self._animation_timeout_id = None

        if self.active:
            self.sni_service.set_icon("io.github.slgobinath.SafeEyes-enabled")
        else:
            self.sni_service.set_icon("io.github.slgobinath.SafeEyes-disabled")


def init(ctx, safeeyes_cfg, plugin_config):
    """Initialize the tray icon."""
    global tray_icon
    global safeeyes_config
    logging.debug("Initialize Tray Icon plugin")
    safeeyes_config = safeeyes_cfg
    if not tray_icon:
        tray_icon = TrayIcon(ctx, plugin_config)
    else:
        tray_icon.initialize(plugin_config)


def update_next_break(break_obj, next_break_time):
    """Update the next break time."""
    tray_icon.next_break_time(next_break_time)


def on_pre_break(break_obj):
    """Disable the menu if strict_break is enabled."""
    if safeeyes_config.get("strict_break"):
        tray_icon.lock_menu()
    tray_icon.start_animation()


def on_start_break(break_obj):
    tray_icon.stop_animation()


def on_stop_break():
    tray_icon.unlock_menu()


def on_start():
    """Enable the tray icon."""
    tray_icon.enable_ui()


def on_stop():
    """Disable the tray icon."""
    tray_icon.disable_ui()


def disable() -> None:
    """Disable the tray icon plugin."""
    global tray_icon

    if tray_icon:
        tray_icon.unregister()
        tray_icon = None
