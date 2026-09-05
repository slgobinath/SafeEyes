# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2017  Gobinath
# Copyright (C) 2026  Mel Dafert <m@dafert.at>

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

import json
import pathlib
import pytest

from safeeyes import configuration
from safeeyes import utility


class TestConfigLoad:
    """Test Config.load() and the config_version-based merge mechanism."""

    def write_config(self, tmp_path: pathlib.Path, filename: str, config: dict) -> str:
        config_path = tmp_path / filename
        config_path.write_text(json.dumps(config))
        return str(config_path)

    @staticmethod
    def _noop_create_startup_entry(cls, force=False):
        return None

    def mock_config_paths(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: pathlib.Path,
        user_config: dict,
        system_config: dict,
    ) -> None:
        user_path = self.write_config(tmp_path, "user_config.json", user_config)
        system_path = self.write_config(tmp_path, "system_config.json", system_config)

        monkeypatch.setattr(utility, "CONFIG_FILE_PATH", user_path)
        monkeypatch.setattr(utility, "SYSTEM_CONFIG_FILE_PATH", system_path)

        # Avoid touching the real plugin directories and the autostart entry.
        monkeypatch.setattr(utility, "merge_plugins", lambda config: None)
        monkeypatch.setattr(
            configuration.Config,
            "_create_startup_entry",
            classmethod(self._noop_create_startup_entry),
        )

    def test_load_merges_new_key_from_system_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """An older user config gets the new skip_system_shortcuts_inhibition key
        merged in while keeping customizations.
        """
        old_user_config = {
            "meta": {"config_version": "6.0.5"},
            "strict_break": True,
            "short_break_interval": 20,
        }
        system_config = {
            "meta": {"config_version": "6.0.6"},
            "skip_system_shortcuts_inhibition": False,
            "strict_break": False,
            "short_break_interval": 15,
        }

        self.mock_config_paths(monkeypatch, tmp_path, old_user_config, system_config)

        cfg = configuration.Config.load()

        # The new key is added with its default value...
        assert cfg.get("skip_system_shortcuts_inhibition", None) is False
        # ...while the user's custom values are preserved.
        assert cfg.get("strict_break", None) is True
        assert cfg.get("short_break_interval", None) == 20

        # The merged config is written back to disk with the new version.
        written = json.loads((tmp_path / "user_config.json").read_text())
        assert written["meta"]["config_version"] == "6.0.6"
        assert written["skip_system_shortcuts_inhibition"] is False
        assert written["strict_break"] is True
        assert written["short_break_interval"] == 20

    def test_load_same_version_does_not_merge(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """A user config already on the current version is left untouched."""
        user_config = {
            "meta": {"config_version": "6.0.6"},
            "strict_break": True,
        }
        system_config = {
            "meta": {"config_version": "6.0.6"},
            "skip_system_shortcuts_inhibition": False,
            "strict_break": False,
        }

        self.mock_config_paths(monkeypatch, tmp_path, user_config, system_config)

        cfg = configuration.Config.load()

        # No merge happened: the key is only available via the system config
        # fallback, and the user's value is still used.
        assert cfg.get("skip_system_shortcuts_inhibition", None) is False
        assert cfg.get("strict_break", None) is True

        # The user config on disk was not rewritten.
        written = json.loads((tmp_path / "user_config.json").read_text())
        assert written == user_config
