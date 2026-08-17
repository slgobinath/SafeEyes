"""Conftest for Safe Eyes tests.

Mocks gi and related modules so that tests can import plugins
without requiring PyGObject/GTK libraries to be installed.
"""

import sys
from unittest import mock

# Mock gi and its submodules before any plugin imports
_gi_mock = mock.MagicMock()
_gio_mock = mock.MagicMock()
_glib_mock = mock.MagicMock()

_gi_mock.repository.Gio = _gio_mock
_gi_mock.repository.GLib = _glib_mock

sys.modules.setdefault("gi", _gi_mock)
sys.modules.setdefault("gi.repository", _gi_mock.repository)
sys.modules.setdefault("gi.repository.Gio", _gio_mock)
sys.modules.setdefault("gi.repository.GLib", _glib_mock)
