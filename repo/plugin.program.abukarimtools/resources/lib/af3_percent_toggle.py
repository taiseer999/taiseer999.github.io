# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""
af3_percent_toggle.py - ABUKARIM TOOLS (4.12.31)

Toggles entry "AF3: Watched percentage". Taiseer's AF3 (50.12.7+) shows the
watched percentage as a number (e.g. 45%) in a small pill above the progress
circle on posters and thumbnails. It is on by default; this switch flips the
AF3 skin bool abk.hidepercent. The condition is read live, no skin reload.
"""
import os

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

SKIN_ID = 'skin.arctic.fuse.3'
SETTING = 'abk.hidepercent'
TITLE = 'ABUKARIM TOOLS'
MARK = 'Skin.HasSetting(abk.hidepercent)'


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools WatchedPercent] %s' % msg, level)


def percent_on():
    return not xbmc.getCondVisibility('Skin.HasSetting(%s)' % SETTING)


def skin_supports():
    """True when the installed AF3 has the percentage pill (50.12.7+)."""
    try:
        path = os.path.join(xbmcvfs.translatePath('special://home/addons/%s/' % SKIN_ID),
                            '1080i', 'Includes_Objects.xml')
        with open(path, 'r', encoding='utf-8') as f:
            return MARK in f.read()
    except Exception:
        return False


def set_on(on):
    if on:
        xbmc.executebuiltin('Skin.Reset(%s)' % SETTING)
    else:
        xbmc.executebuiltin('Skin.SetBool(%s)' % SETTING)
    _log('watched percentage: %s' % ('ON' if on else 'OFF'))
    return 'watched percentage %s' % ('on' if on else 'off')


def run():
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        xbmcgui.Dialog().ok(TITLE, T(30440))          # AF3 is not installed
        return
    if xbmc.getSkinDir() != SKIN_ID:
        xbmcgui.Dialog().ok(TITLE, T(30602))          # switch to AF3 first
        return
    if not skin_supports():
        xbmcgui.Dialog().ok(TITLE, T(32371))          # needs AF3 50.12.7 or newer
        return
    if percent_on():
        set_on(False)
        msg = T(32370)
    else:
        set_on(True)
        msg = T(32369)
    xbmcgui.Dialog().notification(TITLE, msg, xbmcgui.NOTIFICATION_INFO, 3000)
    xbmc.executebuiltin('Container.Refresh')
