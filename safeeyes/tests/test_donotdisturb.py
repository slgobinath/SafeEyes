# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2026  Safe Eyes Contributors

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

from unittest import mock


from safeeyes.plugins.donotdisturb import plugin

_PATCH_DBUS = "safeeyes.plugins.donotdisturb.plugin.Gio.DBusProxy"
_PATCH_LOGGING = "safeeyes.plugins.donotdisturb.plugin.logging"


class TestParseSpaceSeparatedList:
    def test_empty_string(self):
        assert plugin._parse_space_separated_list("") == []

    def test_single_item(self):
        assert plugin._parse_space_separated_list("caffeine") == ["caffeine"]

    def test_multiple_items(self):
        result = plugin._parse_space_separated_list("caffeine Totem Firefox")
        assert result == ["caffeine", "totem", "firefox"]

    def test_extra_whitespace(self):
        result = plugin._parse_space_separated_list("  caffeine   totem  ")
        assert result == ["caffeine", "totem"]


def _make_dbus_proxy_mock(inhibited_actions: int):
    """Create a mock Gio.DBusProxy that returns the given InhibitedActions value."""
    proxy = mock.MagicMock()
    prop = mock.MagicMock()
    prop.unpack.return_value = inhibited_actions
    proxy.get_cached_property.return_value = prop
    return proxy


def _make_inhibitor_proxy_mock(app_id: str, flags: int, reason: str = ""):
    """Create a mock for an individual inhibitor's DBus proxy.

    DBus call_sync returns GLib.Variant tuples, so unpack() returns a tuple.
    """
    proxy = mock.MagicMock()

    def call_sync_side_effect(method, *args, **kwargs):
        variant = mock.MagicMock()
        if method == "GetAppId":
            variant.unpack.return_value = (app_id,)
        elif method == "GetReason":
            variant.unpack.return_value = (reason,)
        elif method == "GetFlags":
            variant.unpack.return_value = (flags,)
        return variant

    proxy.call_sync.side_effect = call_sync_side_effect
    return proxy


def _make_session_proxy_mock(inhibited_actions: int, inhibitor_paths: list):
    """Create a session proxy mock for get_active_inhibitors.

    Since get_active_inhibitors() creates its own session proxy, we need a
    second session proxy mock that responds to GetInhibitors.
    """
    proxy = mock.MagicMock()
    inhibitors_variant = mock.MagicMock()
    inhibitors_variant.unpack.return_value = (inhibitor_paths,)
    proxy.call_sync.return_value = inhibitors_variant
    return proxy


class TestInit:
    def test_init_populates_ignored_inhibitor_apps(self):
        """init() should populate ignored_inhibitor_apps from config."""
        plugin_config = {
            "skip_break_windows": "",
            "take_break_windows": "",
            "unfullscreen": True,
            "while_on_battery": False,
            "ignored_inhibitor_apps": "caffeine-gnome-extension Zoom",
        }
        plugin.init(mock.MagicMock(), {}, plugin_config)
        assert plugin.ignored_inhibitor_apps == {"caffeine-gnome-extension", "zoom"}

    def test_init_missing_key_defaults_to_empty(self):
        """init() should default to empty set when key is missing."""
        plugin_config = {
            "skip_break_windows": "",
            "take_break_windows": "",
            "unfullscreen": True,
            "while_on_battery": False,
        }
        plugin.init(mock.MagicMock(), {}, plugin_config)
        assert plugin.ignored_inhibitor_apps == set()


class TestIsIdleInhibitedGnome:
    """Tests for is_idle_inhibited_gnome with ignored_inhibitor_apps."""

    def test_not_inhibited_returns_false(self):
        """When InhibitedActions has no idle bit, return False regardless."""
        with mock.patch(_PATCH_DBUS) as mock_proxy_cls:
            mock_proxy_cls.new_for_bus_sync.return_value = _make_dbus_proxy_mock(0)
            plugin.ignored_inhibitor_apps = set()
            assert plugin.is_idle_inhibited_gnome() is False

    def test_inhibited_no_exceptions_returns_true(self):
        """When idle is inhibited and no exceptions configured, return True.

        GetInhibitors should NOT be called (fast path).
        """
        session_proxy = _make_dbus_proxy_mock(0b1000)
        with mock.patch(_PATCH_DBUS) as mock_proxy_cls:
            mock_proxy_cls.new_for_bus_sync.return_value = session_proxy
            plugin.ignored_inhibitor_apps = set()
            assert plugin.is_idle_inhibited_gnome() is True
            session_proxy.call_sync.assert_not_called()

    def test_inhibited_all_ignored_returns_false(self):
        """When idle is inhibited but all inhibitors are ignored, return False."""
        session_proxy = _make_dbus_proxy_mock(0b1000)
        inhibitor_paths = ["/org/gnome/SessionManager/Inhibitor1"]
        session_proxy2 = _make_session_proxy_mock(0b1000, inhibitor_paths)

        inhibitor_proxy = _make_inhibitor_proxy_mock("caffeine-gnome-extension", 0b1000)

        with mock.patch(_PATCH_DBUS) as mock_proxy_cls:
            mock_proxy_cls.new_for_bus_sync.side_effect = [
                session_proxy,
                session_proxy2,
                inhibitor_proxy,
            ]
            plugin.ignored_inhibitor_apps = {"caffeine-gnome-extension"}
            assert plugin.is_idle_inhibited_gnome() is False

    def test_inhibited_some_not_ignored_returns_true(self):
        """When idle is inhibited and a non-ignored inhibitor exists, return True."""
        session_proxy = _make_dbus_proxy_mock(0b1000)
        inhibitor_paths = [
            "/org/gnome/SessionManager/Inhibitor1",
            "/org/gnome/SessionManager/Inhibitor2",
        ]
        session_proxy2 = _make_session_proxy_mock(0b1000, inhibitor_paths)

        caffeine_proxy = _make_inhibitor_proxy_mock("caffeine-gnome-extension", 0b1000)
        totem_proxy = _make_inhibitor_proxy_mock("org.gnome.Totem", 0b1000)

        with mock.patch(_PATCH_DBUS) as mock_proxy_cls:
            mock_proxy_cls.new_for_bus_sync.side_effect = [
                session_proxy,
                session_proxy2,
                caffeine_proxy,
                totem_proxy,
            ]
            plugin.ignored_inhibitor_apps = {"caffeine-gnome-extension"}
            assert plugin.is_idle_inhibited_gnome() is True

    def test_inhibited_non_idle_inhibitor_not_ignored_returns_false(self):
        """When a non-ignored inhibitor exists but lacks idle flag, return False."""
        session_proxy = _make_dbus_proxy_mock(0b1000)
        inhibitor_paths = [
            "/org/gnome/SessionManager/Inhibitor1",
            "/org/gnome/SessionManager/Inhibitor2",
        ]
        session_proxy2 = _make_session_proxy_mock(0b1000, inhibitor_paths)

        caffeine_proxy = _make_inhibitor_proxy_mock("caffeine-gnome-extension", 0b1000)
        # This inhibitor has flag 0b0100 (suspend inhibit, NOT idle)
        other_proxy = _make_inhibitor_proxy_mock("org.gnome.PowerManager", 0b0100)

        with mock.patch(_PATCH_DBUS) as mock_proxy_cls:
            mock_proxy_cls.new_for_bus_sync.side_effect = [
                session_proxy,
                session_proxy2,
                caffeine_proxy,
                other_proxy,
            ]
            plugin.ignored_inhibitor_apps = {"caffeine-gnome-extension"}
            assert plugin.is_idle_inhibited_gnome() is False

    def test_dbus_error_during_enumeration_falls_back_to_true(self):
        """When GetInhibitors fails, fall back to bitfield result (True)."""
        session_proxy = _make_dbus_proxy_mock(0b1000)
        # get_active_inhibitors creates its own session_proxy2 that fails on
        # GetInhibitors
        session_proxy2 = mock.MagicMock()
        session_proxy2.call_sync.side_effect = Exception("DBus error")

        with mock.patch(_PATCH_DBUS) as mock_proxy_cls:
            mock_proxy_cls.new_for_bus_sync.side_effect = [
                session_proxy,
                session_proxy2,
            ]
            plugin.ignored_inhibitor_apps = {"caffeine-gnome-extension"}
            assert plugin.is_idle_inhibited_gnome() is True

    def test_case_insensitive_matching(self):
        """App IDs should be compared case-insensitively."""
        session_proxy = _make_dbus_proxy_mock(0b1000)
        inhibitor_paths = ["/org/gnome/SessionManager/Inhibitor1"]
        session_proxy2 = _make_session_proxy_mock(0b1000, inhibitor_paths)

        inhibitor_proxy = _make_inhibitor_proxy_mock("Caffeine-GNOME-Extension", 0b1000)

        with mock.patch(_PATCH_DBUS) as mock_proxy_cls:
            mock_proxy_cls.new_for_bus_sync.side_effect = [
                session_proxy,
                session_proxy2,
                inhibitor_proxy,
            ]
            plugin.ignored_inhibitor_apps = {"caffeine-gnome-extension"}
            assert plugin.is_idle_inhibited_gnome() is False


class TestIsIdleInhibitedKde:
    """Tests for KDE warning when ignored_inhibitor_apps is set."""

    def test_kde_logs_warning_when_exceptions_configured(self):
        """KDE should log a warning when ignored_inhibitor_apps is non-empty."""
        kde_proxy = mock.MagicMock()
        prop = mock.MagicMock()
        prop.unpack.return_value = True
        kde_proxy.get_cached_property.return_value = prop

        with mock.patch(_PATCH_DBUS) as mock_proxy_cls:
            mock_proxy_cls.new_for_bus_sync.return_value = kde_proxy
            plugin.ignored_inhibitor_apps = {"caffeine"}
            plugin._kde_warning_logged = False

            with mock.patch(_PATCH_LOGGING) as mock_logging:
                result = plugin.is_idle_inhibited_kde()
                assert result is True
                mock_logging.warning.assert_called_once()
                assert "not supported on KDE" in mock_logging.warning.call_args[0][0]

    def test_kde_warning_logged_only_once(self):
        """KDE warning should only be logged once across multiple calls."""
        kde_proxy = mock.MagicMock()
        prop = mock.MagicMock()
        prop.unpack.return_value = True
        kde_proxy.get_cached_property.return_value = prop

        with mock.patch(_PATCH_DBUS) as mock_proxy_cls:
            mock_proxy_cls.new_for_bus_sync.return_value = kde_proxy
            plugin.ignored_inhibitor_apps = {"caffeine"}
            plugin._kde_warning_logged = False

            with mock.patch(_PATCH_LOGGING) as mock_logging:
                plugin.is_idle_inhibited_kde()
                plugin.is_idle_inhibited_kde()
                assert mock_logging.warning.call_count == 1
