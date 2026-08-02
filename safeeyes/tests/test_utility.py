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

import pytest

from safeeyes import utility


class TestDesktopEnvironment:
    """Test desktop_environment() desktop detection."""

    @staticmethod
    def set_session(
        monkeypatch: pytest.MonkeyPatch,
        desktop_session: str | None,
        current_desktop: str | None,
    ) -> None:
        """Set the session env vars and reset the cached detection."""
        monkeypatch.setattr(utility, "DESKTOP_ENVIRONMENT", None)
        if desktop_session is None:
            monkeypatch.delenv("DESKTOP_SESSION", raising=False)
        else:
            monkeypatch.setenv("DESKTOP_SESSION", desktop_session)
        if current_desktop is None:
            monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
        else:
            monkeypatch.setenv("XDG_CURRENT_DESKTOP", current_desktop)
        # Make sure no other session hints interfere
        monkeypatch.delenv("GNOME_DESKTOP_SESSION_ID", raising=False)
        monkeypatch.delenv("KDE_FULL_SESSION", raising=False)

    def test_gnome_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A plain GNOME session (Fedora/Arch) is detected as gnome."""
        self.set_session(monkeypatch, "gnome", "GNOME")
        assert utility.desktop_environment() == "gnome"

    def test_gnome_wayland_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GNOME Wayland (gnome-wayland) is detected as gnome."""
        self.set_session(monkeypatch, "gnome-wayland", "GNOME")
        assert utility.desktop_environment() == "gnome"

    def test_ubuntu_gnome_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ubuntu GNOME is detected as gnome via XDG_CURRENT_DESKTOP."""
        self.set_session(monkeypatch, "ubuntu", "ubuntu:GNOME")
        assert utility.desktop_environment() == "gnome"

    def test_ubuntu_unity_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ubuntu without a GNOME XDG_CURRENT_DESKTOP keeps the unity fallback."""
        self.set_session(monkeypatch, "ubuntu", "Unity")
        assert utility.desktop_environment() == "unity"

    def test_kde_plasma_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """KDE Plasma is detected as kde."""
        self.set_session(monkeypatch, "plasma", "KDE")
        assert utility.desktop_environment() == "kde"

    def test_gnome_via_current_desktop_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GNOME is detected from XDG_CURRENT_DESKTOP even without DESKTOP_SESSION."""
        self.set_session(monkeypatch, None, "GNOME")
        assert utility.desktop_environment() == "gnome"

    def test_sway_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A real sway session (DESKTOP_SESSION=sway) is detected as sway."""
        self.set_session(monkeypatch, "sway", "sway")
        assert utility.desktop_environment() == "sway"

    def test_sway_via_current_desktop_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sway is detected from XDG_CURRENT_DESKTOP without DESKTOP_SESSION."""
        self.set_session(monkeypatch, None, "sway")
        assert utility.desktop_environment() == "sway"

    def test_ubuntu_gnome_via_current_desktop_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ubuntu GNOME is detected even without DESKTOP_SESSION."""
        self.set_session(monkeypatch, None, "ubuntu:GNOME")
        assert utility.desktop_environment() == "gnome"


class TestIsGnomeWayland:
    """Test is_gnome_wayland() gating helper."""

    @staticmethod
    def set_environment(
        monkeypatch: pytest.MonkeyPatch, is_wayland: bool, desktop: str
    ) -> None:
        monkeypatch.setattr(utility, "is_wayland", lambda: is_wayland)
        monkeypatch.setattr(utility, "desktop_environment", lambda: desktop)

    def test_gnome_wayland(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """True on GNOME Wayland."""
        self.set_environment(monkeypatch, True, "gnome")
        assert utility.is_gnome_wayland() is True

    def test_kde_wayland(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """False on KDE Wayland."""
        self.set_environment(monkeypatch, True, "kde")
        assert utility.is_gnome_wayland() is False

    def test_gnome_x11(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """False on GNOME X11."""
        self.set_environment(monkeypatch, False, "gnome")
        assert utility.is_gnome_wayland() is False
