#!/usr/bin/env python
# Safe Eyes - Screen Share Do Not Disturb plugin
# Skips breaks while a screen share is active (detected via PipeWire).
#
# Copyright (C) 2025  Archisman Panigrahi <apandada1@gmail.com>
# License: GPL-3.0-or-later
# This program was written with the help of copilot

import json
import shutil
import subprocess
from typing import Any, Dict, List

# Plugin globals populated at init
_context = None
_config: Dict[str, Any] = {}

# Default heuristics: known producers and keywords commonly present
_DEFAULT_PRODUCERS = {
    "gnome-shell",
    "gnome-shell-wayland",
    "mutter",
    "kwin",
    "kwin_x11",
    "kwin_wayland",
    "xdg-desktop-portal-wlr",
    "xdg-desktop-portal-gnome",
    "xdg-desktop-portal-kde",
    "wlroots",
    "gamescope",
}
_DEFAULT_KEYWORDS = {"screencast", "screen", "desktop", "monitor"}

# Avoid spamming logs if pw-dump is missing
_checked_pw_dump = False
_has_pw_dump = False


def _load_config(plugin_config: Dict[str, Any]) -> None:
    global _config
    # Allow users to extend or override heuristics if needed
    _config = {
        "producers": set(_DEFAULT_PRODUCERS)
        | set(map(str.lower, plugin_config.get("producers", []))),
        "keywords": set(_DEFAULT_KEYWORDS)
        | set(map(str.lower, plugin_config.get("keywords", []))),
        # Set to True to log each Video/Source node we see (debugging)
        "log_nodes": bool(plugin_config.get("log_nodes", False)),
    }


def _ensure_pw_dump() -> bool:
    global _checked_pw_dump, _has_pw_dump
    if not _checked_pw_dump:
        _has_pw_dump = shutil.which("pw-dump") is not None
        _checked_pw_dump = True
    return _has_pw_dump


def _pw_dump_nodes() -> List[Dict[str, Any]]:
    """
    Returns a list of PipeWire node objects (JSON) or an empty list on failure.
    Uses `pw-dump -N` to keep output minimal.
    """
    if not _ensure_pw_dump():
        return []

    try:
        out = subprocess.check_output(["pw-dump", "-N"], text=True)
        nodes = json.loads(out)
        if not isinstance(nodes, list):
            return []
        return nodes
    except Exception:
        return []


def _node_is_screencast(node: Dict[str, Any]) -> bool:
    """
    Heuristic to decide if a PipeWire node corresponds to a screen share.
    Looks for media.class == Video/Source and compositor/portal producers,
    or descriptive hints like 'screen'/'screencast' in node metadata.
    """
    if node.get("type") != "PipeWire:Interface:Node":
        return False

    props = (node.get("info") or {}).get("props") or {}
    if props.get("media.class") != "Video/Source":
        return False

    app_name = str(props.get("application.name", "")).lower()
    node_name = str(props.get("node.name", "")).lower()
    node_desc = str(props.get("node.description", "")).lower()

    producers = _config.get("producers", _DEFAULT_PRODUCERS)
    keywords = _config.get("keywords", _DEFAULT_KEYWORDS)

    if app_name in producers:
        return True

    text = f"{node_name} {node_desc}"
    if any(k in text for k in keywords):
        return True

    return False


def _is_screencast_active_pipewire() -> bool:
    nodes = _pw_dump_nodes()
    if not nodes:
        return False

    for n in nodes:
        if _node_is_screencast(n):
            props = (n.get("info") or {}).get("props") or {}
            app_name = props.get("application.name", None)
            if app_name:
                print(f"Screen sharing app detected: {app_name}")
            else:
                print("Screen sharing app detected: Unknown")
            return True

    return False


def init(ctx, safeeyes_config, plugin_config):
    global _context
    _context = ctx
    _load_config(plugin_config or {})


def on_pre_break(break_obj):
    """
    Lifecycle method executes before the pre-break period.
    Return True to skip break.
    """
    if _is_screencast_active_pipewire():
        return True
    return False


def on_start_break(break_obj):
    """
    Lifecycle method executes just before the break.
    Return True to skip break.
    """
    if _is_screencast_active_pipewire():
        return True
    return False
