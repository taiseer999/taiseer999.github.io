# -*- coding: utf-8 -*-
import os

import xbmcaddon
import xbmcvfs

ADDON_ID = 'plugin.video.dexhub'


def addon():
    try:
        return xbmcaddon.Addon(ADDON_ID)
    except Exception:
        return xbmcaddon.Addon()


def profile_path():
    path = xbmcvfs.translatePath(addon().getAddonInfo('profile'))
    os.makedirs(path, exist_ok=True)
    return path
