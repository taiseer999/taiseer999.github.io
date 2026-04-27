# -*- coding: utf-8 -*-
"""Session store for active playback context.

Uses Kodi's Home window properties as the primary store (RAM, ~100x faster
than disk on every read/write). Falls back to a profile JSON file only when
xbmcgui isn't available (rare — happens during very early service startup
before the GUI is initialized).

The session is consulted on every progress tick by CompanionPlayer, so the
property-vs-file difference compounds quickly.
"""
import json
import os

from dexhub.common import profile_path

SESSION_FILE = os.path.join(profile_path(), "current_session.json")
WINDOW_ID = 10000  # Home window — survives across plugin invocations
PROP_KEY = 'dexhub.session_v1'


def _window():
    try:
        import xbmcgui
        return xbmcgui.Window(WINDOW_ID)
    except Exception:
        return None


def save_session(data):
    payload = json.dumps(data or {}, ensure_ascii=False)
    win = _window()
    if win is not None:
        try:
            win.setProperty(PROP_KEY, payload)
            return
        except Exception:
            pass
    # Fallback: disk
    try:
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        with open(SESSION_FILE, 'w', encoding='utf-8') as fh:
            fh.write(payload)
    except Exception:
        pass


def load_session():
    win = _window()
    if win is not None:
        try:
            raw = win.getProperty(PROP_KEY) or ''
            if raw:
                return json.loads(raw)
        except Exception:
            pass
    # Fallback: disk
    try:
        with open(SESSION_FILE, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return {}


def clear_session():
    win = _window()
    if win is not None:
        try:
            win.clearProperty(PROP_KEY)
        except Exception:
            pass
    try:
        os.remove(SESSION_FILE)
    except FileNotFoundError:
        pass
    except Exception:
        pass
