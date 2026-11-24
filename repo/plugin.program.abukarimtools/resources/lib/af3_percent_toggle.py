# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LicenseRef-ABTools
# Copyright (C) 2025-2026 Taiseer (Abukarim) - AB Tools. All rights reserved, see LICENSE.txt
"""
af3_percent_toggle.py - ABUKARIM TOOLS (4.12.31, 4.12.35)

Toggles entry "AF3: Watched percentage". Taiseer's AF3 shows the watched
percentage as a number (e.g. 45%) in a capsule joined to the progress circle
on posters and thumbnails (50.12.9+; 50.12.7 had a pill above the circle).

Three modes (two AF3 skin bools, read live - no skin reload):
    focused  focused item only (default)  - both bools off
    all      every item                   - abk.percentall
    off      hidden                       - abk.hidepercent
"""
import os

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.i18n import T

SKIN_ID = 'skin.arctic.fuse.3'
SETTING = 'abk.hidepercent'
ALL = 'abk.percentall'
TITLE = 'ABUKARIM TOOLS'
MARK = 'Skin.HasSetting(abk.percentall)'
MODES = (('focused', 32374), ('all', 32375), ('off', 32376))


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log('[AbukarimTools WatchedPercent] %s' % msg, level)


def _has(name):
    return bool(xbmc.getCondVisibility('Skin.HasSetting(%s)' % name))


def get_mode():
    if _has(SETTING):
        return 'off'
    return 'all' if _has(ALL) else 'focused'


def percent_on():
    return get_mode() != 'off'


def mode_label(mode=None):
    return T(dict(MODES)[mode or get_mode()])


def skin_supports():
    """True when the installed AF3 has the percentage capsule (50.12.9+)."""
    try:
        path = os.path.join(xbmcvfs.translatePath('special://home/addons/%s/' % SKIN_ID),
                            '1080i', 'Includes_Objects.xml')
        with open(path, 'r', encoding='utf-8') as f:
            return MARK in f.read()
    except Exception:
        return False


def set_mode(mode):
    xbmc.executebuiltin(('Skin.SetBool(%s)' if mode == 'off' else 'Skin.Reset(%s)') % SETTING)
    xbmc.executebuiltin(('Skin.SetBool(%s)' if mode == 'all' else 'Skin.Reset(%s)') % ALL)
    _log('watched percentage: %s' % mode)
    return 'watched percentage %s' % mode


def set_on(on):
    """Kept for callers that only know on/off."""
    return set_mode('focused' if on else 'off')


def run():
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % SKIN_ID):
        xbmcgui.Dialog().ok(TITLE, T(30440))          # AF3 is not installed
        return
    if xbmc.getSkinDir() != SKIN_ID:
        xbmcgui.Dialog().ok(TITLE, T(30602))          # switch to AF3 first
        return
    if not skin_supports():
        xbmcgui.Dialog().ok(TITLE, T(32371))          # needs AF3 50.12.9 or newer
        return
    keys = [k for k, _l in MODES]
    cur = get_mode()
    pick = xbmcgui.Dialog().select(T(32368), [T(l) for _k, l in MODES], preselect=keys.index(cur))
    if pick < 0 or keys[pick] == cur:
        return
    set_mode(keys[pick])
    xbmcgui.Dialog().notification(TITLE, '%s: %s' % (T(32368), mode_label(keys[pick])),
                                  xbmcgui.NOTIFICATION_INFO, 3000)
    xbmc.executebuiltin('Container.Refresh')
