# -*- coding: utf-8 -*-
"""Thin helpers around the Kodi API."""
import os
import sys
from urllib.parse import urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
ICON = os.path.join(ADDON_PATH, 'icon.png')
FANART = os.path.join(ADDON_PATH, 'fanart.jpg')

BASE_URL = sys.argv[0] if sys.argv and sys.argv[0].startswith('plugin://') else 'plugin://%s/' % ADDON_ID
try:
    HANDLE = int(sys.argv[1])
except (IndexError, ValueError):
    HANDLE = -1


def s(string_id):
    return ADDON.getLocalizedString(string_id)


def setting(key):
    return ADDON.getSetting(key)


def setting_bool(key):
    try:
        return ADDON.getSettingBool(key)
    except Exception:
        return ADDON.getSetting(key).lower() == 'true'


def setting_int(key, default=0):
    try:
        return ADDON.getSettingInt(key)
    except Exception:
        try:
            return int(ADDON.getSetting(key))
        except ValueError:
            return default


def set_setting(key, value):
    ADDON.setSetting(key, value)


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[%s] %s' % (ADDON_ID, msg), level)


def debug(msg):
    log(msg, xbmc.LOGDEBUG)


def build_url(**params):
    params = {k: v for k, v in params.items() if v is not None and v != ''}
    return BASE_URL + '?' + urlencode(params)


def notify(message, heading=None, icon=None, time=4000):
    xbmcgui.Dialog().notification(heading or ADDON_NAME, message, icon or ICON, time)


def ok(message, heading=None):
    xbmcgui.Dialog().ok(heading or ADDON_NAME, message)


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
    return path


class Busy(object):
    """Context manager showing Kodi's busy spinner."""

    def __enter__(self):
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        return self

    def __exit__(self, *exc):
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
        return False
